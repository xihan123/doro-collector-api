import logging
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import transaction_context
from app.models.sticker import Sticker
from app.models.user_action import UserAction
from app.schemas.sticker import StickerUpdate
from app.services.doro_classifier import doro_classifier
from app.services.image_upload_service import image_upload_service
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)


class StickerService:
    def create_sticker(self, db: Session, image_bytes: bytes) -> Dict[str, Any]:
        """处理上传的图片并创建表情包记录"""
        try:
            # 步骤1: 使用DORO分类器检查是否为DORO表情包
            doro_result = doro_classifier.predict(image_bytes)
            logger.debug(f"DORO分类结果: {doro_result}")

            if not doro_result["is_doro"] or doro_result["confidence"] < 0.6:
                return {
                    "success": False,
                    "message": "上传的图片不是DORO表情包，或DORO可能性较低",
                    "details": doro_result
                }

            # 步骤2: 使用AI直接生成描述（同时检测是否有文字）
            description, has_text = ocr_service.generate_description_with_text_detection(image_bytes)
            logger.debug(f"OCR识别结果: 描述={description}, 有文字={has_text}")

            # 步骤3: 上传到图床
            upload_result = image_upload_service.upload_image(image_bytes)
            logger.debug(f"图片上传结果: {upload_result}")

            if not upload_result["success"]:
                return {
                    "success": False,
                    "message": "上传到图床失败",
                    "details": upload_result
                }

            # 步骤4: 检查MD5是否已存在
            existing_sticker = db.query(Sticker).filter(Sticker.md5 == upload_result["md5"]).first()
            if existing_sticker:
                return {
                    "success": False,
                    "message": "该表情包已存在",
                    "sticker": existing_sticker.as_dict()
                }

            # 步骤5: 创建数据库记录
            with transaction_context(db) as tx:
                # 提取标签
                tags = []
                if has_text:
                    tags.append("有文字")

                # 创建Sticker对象
                db_sticker = Sticker(
                    md5=upload_result["md5"],
                    url=upload_result["url"],
                    description=description,
                    has_ocr_text=has_text,
                    doro_confidence=float(doro_result["confidence"]),
                    tags=tags,
                    width=upload_result.get("width"),
                    height=upload_result.get("height"),
                    file_size=upload_result.get("size")
                )

                # 保存到数据库
                tx.add(db_sticker)
                tx.flush()  # 确保可以获取ID

                return {
                    "success": True,
                    "message": "表情包上传成功",
                    "sticker": db_sticker.as_dict()
                }

        except SQLAlchemyError as e:
            logger.error(f"数据库操作错误: {str(e)}")
            return {
                "success": False,
                "message": f"数据库操作失败: {str(e)}",
                "details": {"error_type": "database_error"}
            }
        except Exception as e:
            logger.error(f"处理表情包时出错: {str(e)}")
            return {
                "success": False,
                "message": f"处理表情包失败: {str(e)}",
                "details": {"error_type": "processing_error"}
            }

    def get_stickers(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 20,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            search_query: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Tuple[List[Sticker], int]:
        """获取表情包列表，支持分页、排序和搜索"""
        try:
            # 使用安全的属性访问，防止SQL注入
            allowed_sort_fields = {"created_at", "likes", "dislikes"}
            if sort_by not in allowed_sort_fields:
                sort_by = "created_at"

            query = db.query(Sticker)

            # 应用搜索条件
            if search_query:
                query = query.filter(Sticker.description.ilike(f"%{search_query}%"))

            # 应用标签过滤
            if tags:
                for tag in tags:
                    query = query.filter(Sticker.tags.contains([tag]))

            # 计算总数
            total = query.count()

            # 应用排序
            if sort_order.lower() == "desc":
                query = query.order_by(desc(getattr(Sticker, sort_by)))
            else:
                query = query.order_by(getattr(Sticker, sort_by))

            # 应用分页
            stickers = query.offset(skip).limit(limit).all()

            return stickers, total
        except SQLAlchemyError as e:
            logger.error(f"获取表情包列表时发生数据库错误: {e}")
            raise
        except Exception as e:
            logger.error(f"获取表情包列表时发生错误: {e}")
            raise

    def get_sticker(self, db: Session, sticker_id: int) -> Optional[Sticker]:
        """根据ID获取表情包"""
        return db.query(Sticker).filter(Sticker.id == sticker_id).first()

    def get_popular_tags(self, db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        """获取热门标签"""
        try:
            # PostgreSQL查询 - 从tags数组中展开标签并统计出现次数
            result = db.query(
                func.unnest(Sticker.tags).label('tag'),
                func.count().label('count')
            ).group_by('tag').order_by(desc('count')).limit(limit).all()

            # 转换查询结果为字典列表
            return [{"tag": r.tag, "count": r.count} for r in result]
        except Exception as e:
            print(f"获取热门标签时出错: {str(e)}")
            return []

    def get_sticker_by_md5(self, db: Session, md5: str) -> Optional[Sticker]:
        """根据MD5获取表情包"""
        return db.query(Sticker).filter(Sticker.md5 == md5).first()

    def update_sticker(self, db: Session, sticker_id: int, sticker_update: StickerUpdate) -> Optional[Sticker]:
        """更新表情包信息"""
        db_sticker = self.get_sticker(db, sticker_id)
        if not db_sticker:
            return None

        # 更新属性
        update_data = sticker_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_sticker, key, value)

        # 保存到数据库
        db.commit()
        db.refresh(db_sticker)
        return db_sticker

    def get_user_action(self, db: Session, sticker_id: int, ip_address: str) -> Optional[str]:
        """获取用户对表情包的操作（like/dislike）"""
        action = db.query(UserAction).filter(
            UserAction.sticker_id == sticker_id,
            UserAction.ip_address == ip_address
        ).first()

        return action.action if action else None

    def like_sticker(self, db: Session, sticker_id: str, ip_address: str) -> Dict[str, Any]:
        """对表情包点赞，使用事务确保原子性"""
        try:
            with transaction_context(db) as tx:
                db_sticker = tx.query(Sticker).filter(Sticker.id == sticker_id).first()
                if not db_sticker:
                    return {"success": False, "message": "表情包不存在"}

                # 检查用户是否已对此表情包操作过
                existing_action = tx.query(UserAction).filter(
                    UserAction.sticker_id == sticker_id,
                    UserAction.ip_address == ip_address
                ).first()

                if existing_action:
                    if existing_action.action == 'like':
                        # 如果已经点赞，则取消点赞
                        db_sticker.likes = max(0, db_sticker.likes - 1)
                        tx.delete(existing_action)
                        return {
                            "success": True,
                            "message": "取消点赞成��",
                            "sticker": db_sticker.as_dict(),
                            "action": None
                        }
                    else:
                        # 如果已经点踩，则切换为点赞
                        db_sticker.dislikes = max(0, db_sticker.dislikes - 1)
                        db_sticker.likes += 1
                        existing_action.action = 'like'
                        return {
                            "success": True,
                            "message": "从点踩切换为点赞成功",
                            "sticker": db_sticker.as_dict(),
                            "action": "like"
                        }
                else:
                    # 新增点赞记录
                    db_sticker.likes += 1
                    new_action = UserAction(
                        ip_address=ip_address,
                        sticker_id=sticker_id,
                        action='like'
                    )
                    tx.add(new_action)
                    return {
                        "success": True,
                        "message": "点赞成功",
                        "sticker": db_sticker.as_dict(),
                        "action": "like"
                    }
        except SQLAlchemyError as e:
            logger.error(f"点赞操作数据库错误: {e}")
            return {"success": False, "message": f"数据库操作失败: {str(e)}"}
        except Exception as e:
            logger.error(f"点赞操作错误: {e}")
            return {"success": False, "message": f"操作失败: {str(e)}"}

    def dislike_sticker(self, db: Session, sticker_id: int, ip_address: str) -> Dict[str, Any]:
        """对表情包点踩"""
        db_sticker = self.get_sticker(db, sticker_id)
        if not db_sticker:
            return {"success": False, "message": "表情包不存在"}

        # 检查用户是否已对此表情包操作过
        existing_action = db.query(UserAction).filter(
            UserAction.sticker_id == sticker_id,
            UserAction.ip_address == ip_address
        ).first()

        if existing_action:
            if existing_action.action == 'dislike':
                # 如果已经点踩，则取消点踩
                db_sticker.dislikes = max(0, db_sticker.dislikes - 1)
                db.delete(existing_action)
                db.commit()
                return {
                    "success": True,
                    "message": "取消点踩成功",
                    "sticker": db_sticker.as_dict(),
                    "action": None
                }
            else:
                # 如果已经点赞，则切换为点踩
                db_sticker.likes = max(0, db_sticker.likes - 1)
                db_sticker.dislikes += 1
                existing_action.action = 'dislike'
                db.commit()
                return {
                    "success": True,
                    "message": "从点赞切换为点踩成功",
                    "sticker": db_sticker.as_dict(),
                    "action": "dislike"
                }
        else:
            # 新增点踩记录
            db_sticker.dislikes += 1
            new_action = UserAction(
                ip_address=ip_address,
                sticker_id=sticker_id,
                action='dislike'
            )
            db.add(new_action)
            db.commit()
            return {
                "success": True,
                "message": "点踩成功",
                "sticker": db_sticker.as_dict(),
                "action": "dislike"
            }

    def get_stickers_with_user_actions(
            self,
            db: Session,
            ip_address: str,
            skip: int = 0,
            limit: int = 20,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            search_query: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取表情包列表，并包含当前用户的操作状态"""
        # 基本查询与原来的get_stickers相同
        query = db.query(Sticker)

        # 应用搜索条件
        if search_query:
            query = query.filter(Sticker.description.ilike(f"%{search_query}%"))

        # 应用标签过滤
        if tags:
            for tag in tags:
                query = query.filter(Sticker.tags.contains([tag]))

        # 计算总数
        total = query.count()

        # 应用排序
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(Sticker, sort_by)))
        else:
            query = query.order_by(getattr(Sticker, sort_by))

        # 应用分页
        stickers = query.offset(skip).limit(limit).all()

        # 获取用户操作
        sticker_ids = [s.id for s in stickers]
        user_actions = {}

        if sticker_ids:
            actions = db.query(UserAction).filter(
                UserAction.sticker_id.in_(sticker_ids),
                UserAction.ip_address == ip_address
            ).all()

            user_actions = {a.sticker_id: a.action for a in actions}

        # 将用户操作合并到表情包数据中
        result = []
        for sticker in stickers:
            sticker_dict = sticker.as_dict()
            sticker_dict["user_action"] = user_actions.get(sticker.id)
            result.append(sticker_dict)

        return result, total

    def batch_download_stickers(self, db: Session, sticker_ids: List[str]) -> List[Dict[str, Any]]:
        """获取批量下载的表情包信息"""
        stickers = db.query(Sticker).filter(Sticker.id.in_(sticker_ids)).all()
        return [sticker.as_dict() for sticker in stickers]

    def update_sticker_description(self, db: Session, sticker_id: int, description: str) -> Dict[str, Any]:
        """更新表情包描述"""
        try:
            db_sticker = db.query(Sticker).filter(Sticker.id == sticker_id).first()
            if not db_sticker:
                return {"success": False, "message": "表情包不存在"}

            db_sticker.description = description
            db.commit()
            db.refresh(db_sticker)

            return {
                "success": True,
                "message": "表情包描述更新成功",
                "sticker": db_sticker.as_dict(),
                "action": "description"
            }
        except SQLAlchemyError as e:
            logger.error(f"更新表情包描述时发生数据库错误: {e}")
            return {"success": False, "message": f"数据库操作失败: {str(e)}"}
        except Exception as e:
            logger.error(f"更新表情包描述时发生错误: {e}")
            return {"success": False, "message": f"操作失败: {str(e)}"}


# 创建单例实例
sticker_service = StickerService()
