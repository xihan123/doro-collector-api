import time

from sqlalchemy import String, BigInteger
from sqlalchemy import Table, Column, ForeignKey, Integer

from app.db.database import Base

sticker_tags_association_table = Table(
    'sticker_tags',  # Table name in the database
    Base.metadata,
    Column(
        'sticker_id',
        String(36),
        ForeignKey('stickers.id', ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        'tag_id',
        Integer,
        ForeignKey('tags.id', ondelete="CASCADE"),
        primary_key=True
    )
)


class Tag(Base):
    """标签模型，用于存储表情包的标签信息"""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(10), unique=True, index=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(BigInteger, default=(time.time()), nullable=False)
    updated_at = Column(BigInteger, default=(time.time()), onupdate=(time.time()), nullable=False)
