from __future__ import annotations

"""协调OCR请求处理流程的编排器，负责并发控制和资源调度。"""

import asyncio
import logging
import time
from typing import Any, Dict, List

from smart_ocr.config import Settings
from smart_ocr.gpu_manager import GPUWorkerManager
from smart_ocr.image_loader import ImageProcessingError, load_image_from_request
from smart_ocr.models import OCRRequest, OCRResponse, TaskStatus
from smart_ocr.task_tracker import get_task_tracker

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
        self.task_tracker = get_task_tracker()

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

    async def process_request(
        self, request: OCRRequest, track_progress: bool = False
    ) -> OCRResponse:
        """处理单个OCR请求的完整流程。

        该方法会执行以下步骤：
        1. 通过信号量控制并发数，防止系统过载
        2. 加载输入文件（图像或PDF）
        3. 对于PDF，逐页进行OCR识别
        4. 聚合所有识别结果并计算性能指标
        5. 返回标准化的响应对象

        参数:
            request: 客户端提交的OCR请求对象
            track_progress: 是否启用任务进度跟踪

        返回:
            包含所有识别结果和性能指标的响应对象

        异常:
            RuntimeError: 当编排器未初始化时抛出
            ImageProcessingError: 当文件加载或处理失败时抛出
        """
        if not self.gpu_manager:
            raise RuntimeError("OCR编排器尚未初始化，请先调用 start() 方法")

        page_count = 1
        processed_pages = 0
        task_id = None
        tracker = self.task_tracker if track_progress else None
        if tracker:
            task_id = tracker.create_task(total_pages=page_count)

        await self._semaphore.acquire()
        try:
            start_time = time.perf_counter()

            try:
                if tracker and task_id:
                    await tracker.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.PROCESSING,
                        processed_pages=processed_pages,
                        total_pages=page_count,
                    )

                image_list, is_pdf, page_count = await load_image_from_request(
                    image_url=request.image_url,
                    image_base64=request.image_base64,
                    pdf_url=request.pdf_url,
                    pdf_base64=request.pdf_base64,
                    timeout=self.settings.fetch_timeout_seconds,
                    pdf_dpi=self.settings.pdf_render_dpi,
                )

                if tracker and task_id:
                    await tracker.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.PROCESSING,
                        total_pages=page_count,
                        processed_pages=processed_pages,
                    )
            except ImageProcessingError as exc:
                logger.error(f"文件加载失败: {exc}")
                if tracker and task_id:
                    await tracker.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error=str(exc),
                        processed_pages=processed_pages,
                    )
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
                processed_pages = page_idx

                if tracker and task_id:
                    await tracker.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.PROCESSING,
                        processed_pages=processed_pages,
                        total_pages=page_count,
                    )

            duration_ms = (time.perf_counter() - start_time) * 1000

            response_data = {
                "results": all_results,
                "text_count": len(all_results),
                "processing_time": total_processing_time,
                "duration_ms": duration_ms,
                "page_count": page_count,
            }

            if tracker and task_id:
                response_data["task_id"] = task_id
                await tracker.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    processed_pages=page_count,
                    total_pages=page_count,
                    result=response_data,
                )

            return OCRResponse(**response_data)

        except Exception as exc:
            if tracker and task_id:
                await tracker.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    processed_pages=processed_pages,
                    total_pages=page_count,
                    error=str(exc),
                )
            raise

        finally:
            self._semaphore.release()

    async def get_task_status(self, task_id: str) -> Dict[str, Any] | None:
        """查询指定任务的运行状态。

        参数:
            task_id: 任务唯一标识符

        返回:
            包含任务状态信息的字典，若任务不存在返回None
        """
        return await self.task_tracker.get_task_info(task_id)

    async def list_tasks(
        self, status_filter: TaskStatus | None = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取任务列表。

        参数:
            status_filter: 可选的状态过滤条件
            limit: 返回的最大任务数量

        返回:
            任务详情字典列表
        """
        return await self.task_tracker.get_all_tasks(status_filter=status_filter, limit=limit)

    async def get_task_statistics(self) -> Dict[str, Any]:
        """获取当前任务的统计信息。"""

        return await self.task_tracker.get_statistics()
