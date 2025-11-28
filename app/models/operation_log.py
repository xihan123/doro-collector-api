from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Text
from sqlalchemy.dialects.postgresql import ENUM

from app.db.database import Base

# 定义操作类型枚举
operation_type = ENUM('upload', 'update_description', name='operation_type')


class OperationLog(Base):
    """操作日志记录，记录上传和修改描述的操作"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, nullable=False, comment="操作者IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理(User-Agent)")
    sticker_id = Column(
        String(36),  # 与 stickers.id 类型长度一致
        ForeignKey("stickers.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的表情包ID"
    )
    operation = Column(operation_type, nullable=False, comment="操作类型: upload/update_description")
    old_description = Column(String(20), nullable=True, comment="修改前的描述")
    new_description = Column(String(20), nullable=True, comment="修改后的描述")
    operation_time = Column(BigInteger, nullable=False, comment="操作时间戳")

    def __repr__(self):
        return f"<OperationLog(id={self.id}, operation={self.operation}, sticker_id={self.sticker_id})>"
