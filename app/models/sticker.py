import time
import uuid

from sqlalchemy import Column, String, Integer, Float, BigInteger
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.tag import sticker_tags_association_table


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
    tags = relationship("Tag", secondary=sticker_tags_association_table, backref="stickers", cascade="merge")
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)

    # 将模型实例转换为字典
    def as_dict(self):
        return {
            "id": self.id,
            "md5": self.md5,
            "url": self.url,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "likes": self.likes,
            "dislikes": self.dislikes,
            "doro_confidence": self.doro_confidence,
            "tags": [tag.name for tag in self.tags],
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size
        }
