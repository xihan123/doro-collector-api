import base64
import json
import logging
import re
from typing import NamedTuple, Optional, Tuple

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# 内容审核三态结论
VERDICT_SAFE = "safe"
VERDICT_UNSAFE = "unsafe"
VERDICT_REVIEW = "review"

_VALID_VERDICTS = {VERDICT_SAFE, VERDICT_UNSAFE, VERDICT_REVIEW}

_MODERATION_PROMPT = """你是一个表情包内容审核员。请分析这张表情包图片。

【任务】
1. 提取图片中清晰可读的文字内容，没有文字则填空字符串，不超过10个字
2. 按下面的标准判定内容安全性

【只有明确包含以下内容才判 unsafe】
- 色情、裸露或性行为
- 真实血腥场面、残肢、虐待
- 煽动仇恨或辱骂攻击特定人群
- 违法内容（毒品、武器制作、诈骗等）

【以下情形一律判 safe】
- 普通表情包、梗图、聊天常用图
- 轻微粗口或调侃，但不针对特定人群
- 画风搞笑、夸张、奇怪的图片
- AI生成风格的图片（本站表情包多为AI生成角色，"疑似AI生成"不是违规理由）

【以下情形判 review】
- 图片模糊、文字潦草，无法确认内容
- 不确定是否属于上述违规类别

宁可漏放，不可误判：只有确定违规才判 unsafe，拿不准一律判 review。

【输出】只输出JSON，不要输出任何其他内容：
{"description": "图片中的文字", "has_text": true, "verdict": "safe", "reason": "判定理由，不超过30字"}
其中 verdict 只能是 "safe"、"unsafe" 或 "review" 之一。"""


class ModerationResult(NamedTuple):
    """审核结果，verdict 取 safe/unsafe/review"""
    description: str
    has_text: bool
    verdict: str
    reason: str


class OCRService:
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT,
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
                model="Qwen/Qwen3.5-4B",
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
                max_tokens=300
            )

            text = (response.choices[0].message.content or "").strip()
            logger.debug(f'AI OCR返回: {text}')
            has_text = text != "无文字" and len(text) > 0

            return has_text, text if has_text else ""

        except Exception as e:
            logger.error(f"AI OCR错误: {str(e)}")
            return False, ""

    def generate_description(self, image_bytes: bytes) -> str:
        """为表情包生成描述"""
        try:
            return self._ai_describe_image(image_bytes)
        except Exception as e:
            logger.error(f"描述生成错误: {str(e)}")
            return "野生的doro表情包"

    def _ai_describe_image(self, image_bytes: bytes) -> str:
        """使用AI生成图像描述"""
        try:
            # 将图像转换为base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # 调用OpenAI API生成描述
            response = self.openai_client.chat.completions.create(
                model="Qwen/Qwen3.5-4B",
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
                max_tokens=300
            )

            # 获取描述
            description = (response.choices[0].message.content or "").strip()

            # 如果描述太长，截取前10个字
            if len(description) > 10:
                description = description[:10]

            return description if description else "野生的doro表情包"

        except Exception as e:
            logger.error(f"AI描述错误: {str(e)}")
            return "野生的doro表情包"

    @staticmethod
    def _extract_json(reply_text: str) -> Optional[dict]:
        """从模型回复中提取JSON对象，失败返回None"""
        text = reply_text.strip()
        # 去掉 markdown 代码块围栏
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
        # 先尝试整体解析
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        # 再截取第一个 { 到最后一个 } 之间解析
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _to_bool(value, default: bool = False) -> bool:
        """归一化模型返回的布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "yes", "是", "1"):
                return True
            if v in ("false", "no", "否", "0"):
                return False
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        return default

    @staticmethod
    def _normalize_verdict(value) -> str:
        """归一化审核结论，无法识别的按 review 处理"""
        if isinstance(value, str):
            v = value.strip().lower()
            if v in _VALID_VERDICTS:
                return v
            # 常见同义写法
            if v in ("uncertain", "unsure", "unknown"):
                return VERDICT_REVIEW
        return VERDICT_REVIEW

    def generate_description_with_text_detection(self, image_bytes: bytes) -> ModerationResult:
        """使用AI生成描述、检测文字并做内容审核，拿不准或调用失败返回 review"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            response = self.openai_client.chat.completions.create(
                model="Qwen/Qwen3.5-4B",
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
                                "text": _MODERATION_PROMPT
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0,
            )

            reply_text = (response.choices[0].message.content or "").strip()
            json_data = self._extract_json(reply_text)

            if json_data is None:
                logger.warning(f"AI审核回复不是有效JSON，转人工复审: {reply_text[:200]}")
                return ModerationResult(
                    description="野生的doro表情包", has_text=False,
                    verdict=VERDICT_REVIEW, reason="AI回复无法解析，需人工确认"
                )

            description = json_data.get("description", "")
            if not isinstance(description, str):
                description = ""
            description = description.strip()
            if description in ("", "无"):
                description = "野生的doro表情包"
            if len(description) > 10:
                description = description[:10]

            has_text = self._to_bool(json_data.get("has_text"), default=False)
            verdict = self._normalize_verdict(json_data.get("verdict"))
            reason = json_data.get("reason", "")
            if not isinstance(reason, str):
                reason = ""
            reason = reason.strip()[:100]

            logger.info(f"AI审核结果: verdict={verdict}, reason={reason}, description={description}")
            return ModerationResult(
                description=description, has_text=has_text,
                verdict=verdict, reason=reason
            )

        except Exception as e:
            logger.error(f"AI审核服务调用失败: {str(e)}")
            return ModerationResult(
                description="野生的doro表情包", has_text=False,
                verdict=VERDICT_REVIEW, reason=f"AI服务调用失败: {str(e)[:80]}"
            )


# 创建单例实例
ocr_service = OCRService()
