import time
import uuid

from sqlalchemy import Column, String, Integer, Float, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.database import Base


class Sticker(Base):
    __tablename__ = "stickers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    md5 = Column(String(32), unique=True, index=True, nullable=False)
    url = Column(String(255), nullable=False)
    description = Column(String(20), nullable=False)
    created_at = Column(BigInteger, default=lambda: int(time.time()))
    updated_at = Column(BigInteger, default=lambda: int(time.time()),
                        onupdate=lambda: int(time.time()))
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    doro_confidence = Column(Float, default=0.0)
    tags = Column(ARRAY(String), default=list)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)

    # 将模型实例转换为字典
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
