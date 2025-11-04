from __future__ import annotations

import base64
from typing import Optional

import httpx


class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""


async def load_image_from_request(
    image_url: Optional[str],
    image_base64: Optional[str],
    timeout: float,
) -> bytes:
    """Load image bytes from either URL or base64 string."""
    if image_base64:
        try:
            return base64.b64decode(image_base64)
        except Exception as exc:
            raise ImageProcessingError("Failed to decode base64 image") from exc

    if image_url:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return response.content
        except Exception as exc:
            raise ImageProcessingError("Failed to download image from URL") from exc

    raise ImageProcessingError("Either image_url or image_base64 must be provided")
