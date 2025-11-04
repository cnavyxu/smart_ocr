from __future__ import annotations

"""GPU资源管理器，负责多GPU负载均衡和OCR工作进程的调度。"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List

from smart_ocr.config import Settings
from smart_ocr.ocr_service import OCRService

logger = logging.getLogger(__name__)


class GPUWorkerManager:
    """跨多个GPU设备的OCR工作进程管理器。

    该类负责初始化和管理绑定到不同GPU设备的OCR工作进程，
    并通过轮询（Round-Robin）算法实现请求的负载均衡。
    """

    def __init__(self, settings: Settings):
        """初始化GPU工作进程管理器。

        参数:
            settings: 应用配置实例，包含GPU设备ID列表等参数
        """
        self.settings = settings
        self.workers: List[OCRService] = []
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        """为配置中的每个GPU设备初始化一个OCR工作进程。

        该方法会遍历配置的GPU设备ID列表，为每个设备创建独立的
        OCRService实例，并预加载PaddleOCR模型到对应的GPU显存中。
        """
        logger.info(
            f"正在为以下GPU设备初始化OCR工作进程: {self.settings.gpu_device_ids}"
        )

        for gpu_id in self.settings.gpu_device_ids:
            worker = OCRService(
                gpu_id=gpu_id,
                lang=self.settings.paddle_lang,
                use_gpu=self.settings.use_gpu,
            )
            self.workers.append(worker)

        logger.info(f"已成功初始化 {len(self.workers)} 个GPU工作进程")

    async def get_next_worker(self) -> OCRService:
        """使用轮询算法获取下一个可用的OCR工作进程。

        该方法通过异步锁保证线程安全，确保在高并发场景下
        请求能够均匀分配到各个GPU设备上。

        返回:
            下一个可用的OCRService工作进程实例
        """
        async with self._lock:
            worker = self.workers[self._round_robin_index]
            self._round_robin_index = (self._round_robin_index + 1) % len(
                self.workers
            )
            return worker

    @asynccontextmanager
    async def get_worker(self) -> AsyncIterator[OCRService]:
        """上下文管理器，用于获取和释放OCR工作进程。

        该方法提供了一种安全的方式来获取工作进程，确保资源在使用后
        能够正确释放（虽然当前实现中没有显式的释放操作）。

        使用示例:
            async with gpu_manager.get_worker() as worker:
                result = await worker.recognize_image(image_data)

        生成:
            OCRService实例，可用于执行OCR识别任务
        """
        worker = await self.get_next_worker()
        try:
            yield worker
        finally:
            pass

    async def process_ocr_request(self, image_data: bytes) -> Dict:
        """处理单个OCR请求，自动选择最优的GPU工作进程。

        该方法会自动选择一个可用的GPU工作进程，执行OCR识别，
        并记录处理时间等性能指标。

        参数:
            image_data: 待识别的图像二进制数据

        返回:
            包含识别结果和性能指标的字典:
            - results: 识别到的文本区域列表
            - processing_time: OCR推理耗时（秒）
            - text_count: 识别到的文本区域数量
        """
        start_time = time.time()

        async with self.get_worker() as worker:
            results = await worker.recognize_image(image_data)

        processing_time = time.time() - start_time

        return {
            "results": results,
            "processing_time": processing_time,
            "text_count": len(results),
        }

    async def shutdown(self):
        """关闭所有GPU工作进程并清理相关资源。

        该方法会遍历所有工作进程，安全地关闭它们的线程池执行器，
        并清空工作进程列表。
        """
        logger.info("正在关闭GPU工作进程管理器")
        for worker in self.workers:
            worker.shutdown()
        self.workers.clear()
        logger.info("GPU工作进程管理器已关闭")


_manager_instance: GPUWorkerManager | None = None


async def get_gpu_manager() -> GPUWorkerManager:
    """获取全局单例的GPU管理器实例。

    返回:
        全局GPU管理器实例

    异常:
        RuntimeError: 如果GPU管理器尚未初始化
    """
    global _manager_instance
    if _manager_instance is None:
        raise RuntimeError("GPU管理器尚未初始化")
    return _manager_instance


async def initialize_gpu_manager(settings: Settings):
    """初始化全局GPU管理器实例。

    参数:
        settings: 应用配置实例
    """
    global _manager_instance
    _manager_instance = GPUWorkerManager(settings)
    await _manager_instance.initialize()


async def shutdown_gpu_manager():
    """关闭并清理全局GPU管理器实例。"""
    global _manager_instance
    if _manager_instance:
        await _manager_instance.shutdown()
        _manager_instance = None
