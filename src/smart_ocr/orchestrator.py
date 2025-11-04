from __future__ import annotations

import asyncio
import logging
import time

from smart_ocr.config import Settings
from smart_ocr.gpu_manager import GPUWorkerManager
from smart_ocr.image_loader import ImageProcessingError, load_image_from_request
from smart_ocr.models import OCRRequest, OCRResponse

logger = logging.getLogger(__name__)


class OCROrchestrator:
    """Coordinates OCR requests, handling concurrency and error management."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.gpu_manager: GPUWorkerManager | None = None
        self._semaphore = asyncio.Semaphore(self.settings.max_queue_size)

    async def start(self):
        """Initialize orchestrator components."""
        logger.info("Starting OCR orchestrator")
        self.gpu_manager = GPUWorkerManager(self.settings)
        await self.gpu_manager.initialize()

    async def stop(self):
        """Stop orchestrator and release resources."""
        if self.gpu_manager:
            await self.gpu_manager.shutdown()
            self.gpu_manager = None
        logger.info("OCR orchestrator stopped")

    async def process_request(self, request: OCRRequest) -> OCRResponse:
        """Process OCR request with concurrency control."""
        if not self.gpu_manager:
            raise RuntimeError("OCR orchestrator not initialized")

        await self._semaphore.acquire()
        try:
            start_time = time.perf_counter()

            try:
                image_bytes = await load_image_from_request(
                    image_url=request.image_url,
                    image_base64=request.image_base64,
                    timeout=self.settings.fetch_timeout_seconds,
                )
            except ImageProcessingError as exc:
                logger.error(f"Image processing error: {exc}")
                raise

            ocr_result = await self.gpu_manager.process_ocr_request(image_bytes)
            ocr_result["duration_ms"] = (time.perf_counter() - start_time) * 1000
            return OCRResponse(**ocr_result)
        finally:
            self._semaphore.release()
