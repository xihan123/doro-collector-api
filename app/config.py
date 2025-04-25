import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    # 基本配置
    PROJECT_NAME: str = "DORO表情包收集系统"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY")

    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "1"))

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    # 模型配置
    MODEL_PATH: str = os.getenv("MODEL_PATH", "model/model.onnx")

    # OpenAI API配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "30"))

    # 图床API配置
    PICB_API_KEY: str = os.getenv("PICB_API_KEY", "")
    PICB_ALBUM_ID: str = os.getenv("PICB_ALBUM_ID", "")
    PICB_UPLOAD_URL: str = os.getenv("PICB_UPLOAD_URL", "https://www.picb.cc/api/1/upload")
    PICB_TIMEOUT: int = int(os.getenv("PICB_TIMEOUT", "30"))

    # CORS设置
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # 其他设置
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
    PIC_DIR: str = os.getenv("PIC_DIR", "")

    class Config:
        env_file = ".env"


settings = Settings()
