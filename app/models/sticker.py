import time
import uuid

from sqlalchemy import Column, String, Integer, Float, Boolean, ARRAY, BigInteger

from app.db.database import Base


class Sticker(Base):
    __tablename__ = "stickers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    md5 = Column(String, unique=True, index=True)
    url = Column(String, nullable=False)
    description = Column(String, nullable=False)
    has_ocr_text = Column(Boolean, default=False)
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
    created_by_ip = Column(String, nullable=True)

    # 将模型实例转换为字典
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
