import base64
from typing import Tuple

from openai import OpenAI

from app.config import settings


class OCRService:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    def detect_text(self, image_bytes: bytes) -> Tuple[bool, str]:
        """使用AI检测图像中的文本"""
        return self._ai_ocr_text(image_bytes)

    def _ai_ocr_text(self, image_bytes: bytes) -> Tuple[bool, str]:
        """使用AI进行OCR文本检测"""
        try:
            # 将图像转换为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # 调用API检测文本
            response = self.openai_client.chat.completions.create(
                model="Pro/Qwen/Qwen2.5-VL-7B-Instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "这张图片里有文字吗？如果有，请只提取文字内容，否则回答'无文字'。"
                            }
                        ]
                    }
                ],
                max_tokens=50
            )

            text = response.choices[0].message.content.strip()
            print(f'AI OCR返回: {text}')
            has_text = text != "无文字" and len(text) > 0

            return has_text, text if has_text else ""

        except Exception as e:
            print(f"AI OCR错误: {str(e)}")
            return False, ""

    def generate_description(self, image_bytes: bytes) -> str:
        """为表情包生成描述"""
        try:
            return self._ai_describe_image(image_bytes)
        except Exception as e:
            print(f"描述生成错误: {str(e)}")
            return "野生的doro表情包"

    def _ai_describe_image(self, image_bytes: bytes) -> str:
        """使用AI生成图像描述"""
        try:
            # 将图像转换为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # 调用API生成描述
            response = self.openai_client.chat.completions.create(
                model="Pro/Qwen/Qwen2.5-VL-7B-Instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "你是一个专门描述表情包内容的助手，请为以下表情包提取其中文字，具体不能超过10个字"
                            }
                        ]
                    }
                ],
                max_tokens=50
            )

            # 获取描述
            description = response.choices[0].message.content.strip()

            # 如果描述太长，截取前10个字
            if len(description) > 10:
                description = description[:10]

            return description if description else "野生的doro表情包"

        except Exception as e:
            print(f"AI描述错误: {str(e)}")
            return "野生的doro表情包"

    def generate_description_with_text_detection(self, image_bytes: bytes) -> Tuple[str, bool]:
        """
        使用AI一次性生成描述并检测是否有文字

        返回: (描述, 是否有文字)
        """
        try:
            # 转换为base64
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # 调用OpenAI API
            response = ocr_service.openai_client.chat.completions.create(
                model="Pro/Qwen/Qwen2.5-VL-7B-Instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "请为这个表情包提取所有文本内容。请回复JSON格式，包含两个字段：\"description\"(表情包文本，不超过10个字)和\"has_text\"(布尔值，表示表情包中是否包含可识别的文字)"
                            }
                        ]
                    }
                ],
                max_tokens=100
            )

            # 解析回复
            import json
            import re

            # 获取回复内容并尝试提取JSON
            reply_text = response.choices[0].message.content.strip()

            # 使用正则表达式从回复中提取JSON部分
            json_match = re.search(r'({.*})', reply_text, re.DOTALL)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    description = json_data.get("description", "野生的doro表情包")
                    has_text = json_data.get("has_text", False)
                except json.JSONDecodeError:
                    # 如果JSON解析失败，使用默认值
                    description = "野生的doro表情包"
                    has_text = False
            else:
                # 如果没有找到JSON格式，直接使用回复作为描述
                description = reply_text[:10] if len(reply_text) > 10 else reply_text
                has_text = "文字" in reply_text or "字" in reply_text

            # 确保描述不为空
            if not description or description.strip() == "":
                description = "野生的doro表情包"

            # 限制描述长度
            if len(description) > 10:
                description = description[:10]

            return description, has_text

        except Exception as e:
            print(f"生成描述时出错: {str(e)}")
            return "野生的doro表情包", False


# 创建单例实例
ocr_service = OCRService()
