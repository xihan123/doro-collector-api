import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import stickers
from app.config import settings
from app.db.database import engine, Base
from app.middlewares.logging_middleware import LoggingMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)


def upgrade_schema():
    """幂等升级已有表结构，create_all 不会修改已存在的表"""
    statements = [
        "ALTER TABLE stickers ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) NOT NULL DEFAULT 'approved'",
        "ALTER TABLE stickers ADD COLUMN IF NOT EXISTS reviewed_at BIGINT",
        "ALTER TABLE stickers ADD COLUMN IF NOT EXISTS review_reason VARCHAR(255)",
        "CREATE INDEX IF NOT EXISTS ix_stickers_review_status ON stickers (review_status)",
        # 原生 ENUM 的新取值需单独 ALTER TYPE
        "ALTER TYPE operation_type ADD VALUE IF NOT EXISTS 'review'",
    ]
    # ALTER TYPE 需在自动提交事务外执行
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:  # 单条失败不阻断启动
                logger.warning(f"数据库结构升级语句执行失败（可能已存在）: {stmt} -> {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时执行
    logger.info("应用程序启动")

    # 创建数据库表
    logger.info("初始化数据库")
    Base.metadata.create_all(bind=engine)
    upgrade_schema()

    # 确保临时目录存在
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    # 确保图片目录存在
    if settings.PIC_DIR and settings.PIC_DIR != "":
        os.makedirs(settings.PIC_DIR, exist_ok=True)

    yield

    # 关闭时执行
    logger.info("应用程序关闭")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="DORO表情包收集API服务",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 包含路由
app.include_router(stickers.router, prefix="/api/stickers", tags=["stickers"])

# 确保临时目录存在
os.makedirs(settings.TEMP_DIR, exist_ok=True)


@app.get("/")
def read_root():
    """API根路径"""
    return {"message": "欢迎使用DORO表情包收集API", "version": settings.PROJECT_VERSION}


@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS
    )
