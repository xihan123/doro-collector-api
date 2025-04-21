import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时执行
    logger.info("应用程序启动")

    # 创建数据库表
    logger.info("初始化数据库")
    Base.metadata.create_all(bind=engine)

    # 确保临时目录存在
    os.makedirs(settings.TEMP_DIR, exist_ok=True)

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
