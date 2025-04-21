import logging
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import create_engine, QueuePool, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

logger = logging.getLogger(__name__)

# 创建数据库引擎，使用连接池优化
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    poolclass=QueuePool,
    pool_recycle=3600  # 每小时重用连接，避免数据库断开连接
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


# 监听连接池事件
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug("数据库连接已创建")


@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("数据库连接已被检出")


@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("数据库连接已被归还")


# 依赖项，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 事务上下文管理器
@contextmanager
def transaction_context(db: Session):
    """
    事务上下文管理器，用于确保数据库操作的原子性
    使用方法:
    with transaction_context(db) as tx:
        # 执行数据库操作
    """
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"数据库事务错误: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"事务中发生错误: {str(e)}")
        raise


# 获取用户IP的辅助函数
def get_client_ip(request: Request) -> str:
    """获取客户端真实IP地址，处理多级代理情况"""
    # 优先从常用代理头获取
    headers_to_check = [
        "X-Forwarded-For",
        "X-Real-IP",
        "CF-Connecting-IP",  # Cloudflare
        "True-Client-IP"
    ]

    for header in headers_to_check:
        if header in request.headers:
            value = request.headers[header]
            # X-Forwarded-For可能包含多个IP，第一个是客户端的真实IP
            if header == "X-Forwarded-For" and "," in value:
                return value.split(",")[0].strip()
            return value.strip()

    # 如果没有代理头，使用直接的客户端地址
    return request.client.host if request.client else "unknown"