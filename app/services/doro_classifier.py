import io
import logging
import time
from pathlib import Path
from typing import Dict, Any

import numpy as np
import onnxruntime as ort
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class DoroClassifier:
    def __init__(self, model_path: Path = settings.MODEL_PATH):
        self.model_path = model_path
        self.input_size = (320, 320)
        self._load_model()

    def _load_model(self):
        """加载ONNX模型，支持重试机制"""
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                # 配置优化选项
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                sess_options.intra_op_num_threads = 4  # 并行线程数

                # 使用GPU加速如果可用
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

                self.session = ort.InferenceSession(
                    str(self.model_path),
                    sess_options=sess_options,
                    providers=providers
                )

                self.input_name = self.session.get_inputs()[0].name
                self.output_name = self.session.get_outputs()[0].name
                logger.info(f"DORO分类器模型加载成功: {self.model_path}")
                return

            except Exception as e:
                logger.error(f"加载模型失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError(f"无法加载DORO分类模型: {e}")

    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """将图像字节数据预处理为适合模型输入的格式"""
        # 读取图像
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert('RGB')  # 确保图像是RGB格式

        # 调整大小
        image = image.resize(self.input_size)

        # 转换为numpy数组
        img_array = np.array(image).astype(np.float32)

        # 归一化 (使用与训练时相同的均值和标准差)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape((1, 1, 3))
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape((1, 1, 3))
        img_array = ((img_array / 255.0 - mean) / std).astype(np.float32)

        # 调整维度顺序 (HWC -> NCHW)
        img_array = img_array.transpose((2, 0, 1)).reshape(1, 3, *self.input_size)

        return img_array

    def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """预测图像是否为DORO表情包"""
        try:
            start_time = time.time()

            # 预处理图像
            input_data = self.preprocess_image(image_bytes)

            # 运行推理
            results = self.session.run([self.output_name], {self.input_name: input_data})
            output = results[0]

            # 获取概率
            probabilities = self.softmax(output[0])

            # 获取预测类别和置信度
            predicted_class = np.argmax(probabilities)
            confidence = float(probabilities[predicted_class])

            # 假设索引0对应DORO类别
            is_doro = predicted_class == 0

            inference_time = time.time() - start_time
            logger.debug(f"DORO分类器推理完成，耗时: {inference_time:.4f}秒")

            return {
                "is_doro": is_doro,
                "confidence": confidence,
                "probabilities": {
                    "doro": float(probabilities[0]),
                    "non_doro": float(probabilities[1]) if len(probabilities) > 1 else 0.0
                },
                "inference_time_ms": int(inference_time * 1000)
            }

        except Exception as e:
            logger.error(f"DORO分类预测错误: {e}")
            return {
                "is_doro": False,
                "confidence": 0.0,
                "error": str(e),
                "probabilities": {
                    "doro": 0.0,
                    "non_doro": 0.0
                }
            }

    @staticmethod
    def softmax(x: np.ndarray) -> np.ndarray:
        """计算softmax"""
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()


# 创建单例实例
doro_classifier = DoroClassifier()
