import hashlib
import logging
from typing import Any, Dict

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class ImageUploadService:
    def __init__(self, api_key: str, album_id: str, upload_url: str):
        self.api_key = api_key
        self.album_id = album_id
        self.upload_url = upload_url

    def calculate_md5(self, image_bytes: bytes) -> str:
        """计算图像的MD5哈希值"""
        return hashlib.md5(image_bytes).hexdigest()

    def upload_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """上传图像到图床服务并返回结果"""
        try:
            response = requests.post(
                self.upload_url,
                files={"source": ("image.png", image_bytes)},
                data={"album_id": self.album_id},
                headers={"X-API-Key": self.api_key},
                timeout=settings.PICB_TIMEOUT
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()

                # 提取需要的信息
                if result.get("status_code") == 200:
                    image_data = result.get("image", {})
                    return {
                        "success": True,
                        "md5": image_data.get("md5", ""),
                        "url": image_data.get("url", ""),
                        "width": image_data.get("width"),
                        "height": image_data.get("height"),
                        "size": image_data.get("size")
                    }

            # 上传失败
            logger.error(f"图床上传失败: {response.status_code} - {response.text[:200]}")
            return {
                "success": False,
                "error": f"上传失败: {response.status_code} - {response.text}",
                "md5": self.calculate_md5(image_bytes),
                "url": ""
            }

        except Exception as e:
            logger.error(f"图床上传出错: {str(e)}")
            return {
                "success": False,
                "error": f"上传过程中出错: {str(e)}",
                "md5": self.calculate_md5(image_bytes),
                "url": ""
            }


# 创建单例实例
image_upload_service = ImageUploadService(
    api_key=settings.PICB_API_KEY,
    album_id=settings.PICB_ALBUM_ID,
    upload_url=settings.PICB_UPLOAD_URL
)
