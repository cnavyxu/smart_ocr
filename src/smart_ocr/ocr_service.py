from __future__ import annotations

"""PaddleOCR的服务封装，负责执行实际的OCR推理任务。"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from io import BytesIO
from typing import Any, Dict, List, Sequence

import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

logger = logging.getLogger(__name__)


@contextmanager
def _temporary_env(key: str, value: str | None):
    """临时设置环境变量的上下文管理器。

    在上下文生命周期内设置指定的环境变量，退出时自动恢复原值。
    这对于控制CUDA设备可见性非常有用。

    参数:
        key: 环境变量的名称
        value: 要设置的值，如果为None则移除该环境变量

    使用示例:
        with _temporary_env("CUDA_VISIBLE_DEVICES", "0"):
            # 在此代码块中只能看到GPU 0
            model = load_model()
    """
    original = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


class OCRService:
    """绑定到特定GPU设备的PaddleOCR服务封装类。

    该类封装了PaddleOCR引擎，提供异步接口用于图像文本识别。
    每个实例绑定到一个特定的GPU设备，避免多个实例之间的资源竞争。
    """

    def __init__(self, gpu_id: int, lang: str = "ch", use_gpu: bool = True):
        """初始化OCR服务实例。

        参数:
            gpu_id: 要使用的GPU设备编号（0-based）
            lang: PaddleOCR的语言模型标识，如 "ch" (中文)、"en" (英文)
            use_gpu: 是否启用GPU加速，False则使用CPU模式
        """
        self.gpu_id = gpu_id
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr_instance: PaddleOCR | None = None
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"paddleocr-gpu-{gpu_id}"
        )
        logger.info(
            "正在初始化OCR服务 (语言=%s, GPU编号=%s, 使用GPU=%s)",
            self.lang,
            self.gpu_id,
            self.use_gpu,
        )

    def _create_ocr_instance(self) -> PaddleOCR:
        """创建并初始化PaddleOCR实例。

        该方法会临时设置CUDA_VISIBLE_DEVICES环境变量，确保PaddleOCR
        只在指定的GPU设备上加载模型和执行推理。

        返回:
            配置好的PaddleOCR实例
        """
        env_value = str(self.gpu_id) if self.use_gpu else None
        with _temporary_env("CUDA_VISIBLE_DEVICES", env_value):
            logger.info("正在加载PaddleOCR模型到设备 %s", env_value or "CPU")
            return PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False,
            )

    @property
    def ocr(self) -> PaddleOCR:
        """延迟初始化的PaddleOCR实例属性。

        只有在首次访问时才会真正加载模型，避免不必要的资源占用。

        返回:
            PaddleOCR实例
        """
        if self._ocr_instance is None:
            self._ocr_instance = self._create_ocr_instance()
        return self._ocr_instance

    async def recognize_image(self, image_data: bytes) -> List[Dict[str, Any]]:
        """异步执行图像OCR识别。

        该方法将同步的PaddleOCR推理过程包装为异步接口，避免阻塞事件循环。
        实际的OCR推理在独立的线程池中执行。

        参数:
            image_data: 图像文件的二进制数据

        返回:
            识别结果列表，每个元素包含文本内容、置信度和位置信息
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._recognize_sync, image_data
        )

    def _recognize_sync(self, image_data: bytes) -> List[Dict[str, Any]]:
        """同步执行OCR识别的内部方法。

        参数:
            image_data: 图像文件的二进制数据

        返回:
            解析后的识别结果列表
        """
        image = self._bytes_to_image(image_data)
        ocr_result = self.ocr.ocr(image, cls=True)
        return self._parse_result(ocr_result)

    def _bytes_to_image(self, data: bytes) -> np.ndarray:
        """将图像二进制数据转换为RGB格式的NumPy数组。

        参数:
            data: 图像文件的二进制数据（支持常见格式如PNG、JPEG等）

        返回:
            形状为 (height, width, 3) 的NumPy数组，数据类型为uint8
        """
        with BytesIO(data) as buffer:
            image = Image.open(buffer).convert("RGB")
        return np.array(image)

    def _parse_result(self, result: Sequence) -> List[Dict[str, Any]]:
        """解析PaddleOCR的原始输出为标准化的字典格式。

        PaddleOCR的输出结构较为复杂，该方法将其转换为更易使用的格式。

        参数:
            result: PaddleOCR的原始输出结果

        返回:
            标准化的识别结果列表，每个元素包含:
            - text: 识别出的文本内容
            - confidence: 置信度分数 (0-1)
            - position: 文本区域的四个顶点坐标
        """
        parsed: List[Dict[str, Any]] = []
        if not result:
            return parsed

        for image_result in result:
            if not image_result:
                continue
            for line in image_result:
                if not line:
                    continue
                polygon, (text, confidence) = line
                parsed.append(
                    {
                        "text": text,
                        "confidence": float(confidence),
                        "position": {
                            "top_left": polygon[0],
                            "top_right": polygon[1],
                            "bottom_right": polygon[2],
                            "bottom_left": polygon[3],
                        },
                    }
                )
        logger.debug(
            "GPU %s 上的OCR处理完成，识别到 %d 个文本区域",
            self.gpu_id,
            len(parsed),
        )
        return parsed

    def shutdown(self) -> None:
        """释放OCR服务占用的资源。

        关闭线程池执行器，等待所有未完成的任务执行完毕。
        """
        logger.info("正在关闭GPU %s 的OCR服务", self.gpu_id)
        self._executor.shutdown(wait=True)
        logger.info("GPU %s 的OCR服务已关闭", self.gpu_id)
