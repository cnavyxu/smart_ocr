from __future__ import annotations

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
    """Temporarily set an environment variable for the lifetime of the context."""
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
    """OCR service wrapper for PaddleOCR bound to a specific GPU device."""

    def __init__(self, gpu_id: int, lang: str = "ch", use_gpu: bool = True):
        self.gpu_id = gpu_id
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr_instance: PaddleOCR | None = None
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"paddleocr-gpu-{gpu_id}"
        )
        logger.info(
            "Initializing OCR service (lang=%s, gpu_id=%s, use_gpu=%s)",
            self.lang,
            self.gpu_id,
            self.use_gpu,
        )

    def _create_ocr_instance(self) -> PaddleOCR:
        """Create a PaddleOCR instance for the configured GPU."""
        env_value = str(self.gpu_id) if self.use_gpu else None
        with _temporary_env("CUDA_VISIBLE_DEVICES", env_value):
            logger.info("Loading PaddleOCR model on device %s", env_value or "CPU")
            return PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False,
            )

    @property
    def ocr(self) -> PaddleOCR:
        if self._ocr_instance is None:
            self._ocr_instance = self._create_ocr_instance()
        return self._ocr_instance

    async def recognize_image(self, image_data: bytes) -> List[Dict[str, Any]]:
        """Run OCR asynchronously on the provided image bytes."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self._recognize_sync, image_data
        )

    def _recognize_sync(self, image_data: bytes) -> List[Dict[str, Any]]:
        """Synchronous OCR recognition using PaddleOCR."""
        image = self._bytes_to_image(image_data)
        ocr_result = self.ocr.ocr(image, cls=True)
        return self._parse_result(ocr_result)

    def _bytes_to_image(self, data: bytes) -> np.ndarray:
        """Convert raw bytes to an RGB numpy array."""
        with BytesIO(data) as buffer:
            image = Image.open(buffer).convert("RGB")
        return np.array(image)

    def _parse_result(self, result: Sequence) -> List[Dict[str, Any]]:
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
            "OCR processing completed on GPU %s with %d text fragments",
            self.gpu_id,
            len(parsed),
        )
        return parsed

    def shutdown(self) -> None:
        """Release resources associated with this OCR service."""
        logger.info("Shutting down OCR service for GPU %s", self.gpu_id)
        self._executor.shutdown(wait=True)
