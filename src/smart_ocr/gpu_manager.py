from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, List

from smart_ocr.config import Settings
from smart_ocr.ocr_service import OCRService

logger = logging.getLogger(__name__)


class GPUWorkerManager:
    """Manages multiple OCR workers across different GPUs with load balancing."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.workers: List[OCRService] = []
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize OCR workers for each GPU."""
        logger.info(
            f"Initializing GPU workers for devices: {self.settings.gpu_device_ids}"
        )

        for gpu_id in self.settings.gpu_device_ids:
            worker = OCRService(
                gpu_id=gpu_id,
                lang=self.settings.paddle_lang,
                use_gpu=self.settings.use_gpu,
            )
            self.workers.append(worker)

        logger.info(f"Initialized {len(self.workers)} GPU workers")

    async def get_next_worker(self) -> OCRService:
        """Get next available worker using round-robin load balancing."""
        async with self._lock:
            worker = self.workers[self._round_robin_index]
            self._round_robin_index = (self._round_robin_index + 1) % len(
                self.workers
            )
            return worker

    @asynccontextmanager
    async def get_worker(self) -> AsyncIterator[OCRService]:
        """Context manager to acquire and release a worker."""
        worker = await self.get_next_worker()
        try:
            yield worker
        finally:
            pass

    async def process_ocr_request(self, image_data: bytes) -> dict:
        """
        Process OCR request with automatic load balancing.

        Args:
            image_data: Image bytes to process

        Returns:
            OCR results dictionary
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
        """Shut down all workers and clean up resources."""
        logger.info("Shutting down GPU worker manager")
        for worker in self.workers:
            worker.shutdown()
        self.workers.clear()


_manager_instance: GPUWorkerManager | None = None


async def get_gpu_manager() -> GPUWorkerManager:
    """Get the singleton GPU manager instance."""
    global _manager_instance
    if _manager_instance is None:
        raise RuntimeError("GPU manager not initialized")
    return _manager_instance


async def initialize_gpu_manager(settings: Settings):
    """Initialize the global GPU manager."""
    global _manager_instance
    _manager_instance = GPUWorkerManager(settings)
    await _manager_instance.initialize()


async def shutdown_gpu_manager():
    """Shut down the global GPU manager."""
    global _manager_instance
    if _manager_instance:
        await _manager_instance.shutdown()
        _manager_instance = None
