from __future__ import annotations

"""协调OCR请求处理流程的编排器，负责并发控制和资源调度。"""

import asyncio
import logging
import time

from smart_ocr.config import Settings
from smart_ocr.gpu_manager import GPUWorkerManager
from smart_ocr.image_loader import ImageProcessingError, load_image_from_request
from smart_ocr.models import OCRRequest, OCRResponse

logger = logging.getLogger(__name__)


class OCROrchestrator:
    """OCR请求的中央协调器。

    该类负责管理请求队列、并发控制、资源分配和错误处理，
    确保在高并发场景下稳定高效地调度GPU资源进行OCR推理。
    """

    def __init__(self, settings: Settings):
        """初始化OCR编排器。

        参数:
            settings: 应用配置实例，包含所有运行时参数
        """
        self.settings = settings
        self.gpu_manager: GPUWorkerManager | None = None
        self._semaphore = asyncio.Semaphore(self.settings.max_queue_size)

    async def start(self):
        """启动编排器并初始化所有依赖组件。

        该方法会创建并初始化GPU管理器，预加载OCR模型到各个GPU设备上。
        """
        logger.info("正在启动 OCR 编排器")
        self.gpu_manager = GPUWorkerManager(self.settings)
        await self.gpu_manager.initialize()
        logger.info("OCR 编排器启动完成")

    async def stop(self):
        """停止编排器并释放所有占用的资源。

        安全地关闭所有GPU工作进程，并清理相关资源。
        """
        if self.gpu_manager:
            await self.gpu_manager.shutdown()
            self.gpu_manager = None
        logger.info("OCR 编排器已停止")

    async def process_request(self, request: OCRRequest) -> OCRResponse:
        """处理单个OCR请求的完整流程。

        该方法会执行以下步骤：
        1. 通过信号量控制并发数，防止系统过载
        2. 加载输入文件（图像或PDF）
        3. 对于PDF，逐页进行OCR识别
        4. 聚合所有识别结果并计算性能指标
        5. 返回标准化的响应对象

        参数:
            request: 客户端提交的OCR请求对象

        返回:
            包含所有识别结果和性能指标的响应对象

        异常:
            RuntimeError: 当编排器未初始化时抛出
            ImageProcessingError: 当文件加载或处理失败时抛出
        """
        if not self.gpu_manager:
            raise RuntimeError("OCR编排器尚未初始化，请先调用 start() 方法")

        await self._semaphore.acquire()
        try:
            start_time = time.perf_counter()

            try:
                image_list, is_pdf, page_count = await load_image_from_request(
                    image_url=request.image_url,
                    image_base64=request.image_base64,
                    pdf_url=request.pdf_url,
                    pdf_base64=request.pdf_base64,
                    timeout=self.settings.fetch_timeout_seconds,
                    pdf_dpi=self.settings.pdf_render_dpi,
                )
            except ImageProcessingError as exc:
                logger.error(f"文件加载失败: {exc}")
                raise

            all_results = []
            total_processing_time = 0.0

            for page_idx, image_bytes in enumerate(image_list, start=1):
                ocr_result = await self.gpu_manager.process_ocr_request(image_bytes)

                for text_result in ocr_result["results"]:
                    if is_pdf:
                        text_result["page"] = page_idx

                all_results.extend(ocr_result["results"])
                total_processing_time += ocr_result["processing_time"]

            duration_ms = (time.perf_counter() - start_time) * 1000

            response_data = {
                "results": all_results,
                "text_count": len(all_results),
                "processing_time": total_processing_time,
                "duration_ms": duration_ms,
                "page_count": page_count,
            }

            return OCRResponse(**response_data)

        finally:
            self._semaphore.release()
