from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ENUM

from app.db.database import Base

# 定义动作类型枚举
action_type = ENUM('like', 'dislike', name='action_type')


class UserAction(Base):
    """用户操作记录，根据IP追踪用户对表情包的操作"""
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, nullable=False)
    sticker_id = Column(
        String(36),  # 与 stickers.id 类型长度一致
        ForeignKey("stickers.id", ondelete="CASCADE"),
        nullable=False
    )
    action = Column(action_type, nullable=False)  # 'like' or 'dislike'

    # 创建复合索引以加速查询
    __table_args__ = (
        Index('idx_user_action', 'ip_address', 'sticker_id', unique=True),
    )
