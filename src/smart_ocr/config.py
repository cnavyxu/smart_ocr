from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="smart-ocr-service")
    api_prefix: str = Field(default="/v1")
    gpu_device_ids: List[int] = Field(default_factory=lambda: [0, 1, 2])
    use_gpu: bool = Field(default=True)
    paddle_lang: str = Field(default="ch")
    max_queue_size: int = Field(default=100_000)
    max_workers: int = Field(default=32)
    fetch_timeout_seconds: float = Field(default=10.0)
    request_timeout_seconds: float = Field(default=25.0)

    class Config:
        env_prefix = "SMART_OCR_"
        case_sensitive = False

    @validator("gpu_device_ids", pre=True)
    def _parse_gpu_ids(cls, value: object) -> List[int]:
        if value is None:
            return [0, 1, 2]
        if isinstance(value, str):
            ids = [item.strip() for item in value.split(",") if item.strip()]
            return [int(item) for item in ids]
        if isinstance(value, (list, tuple)):
            return [int(item) for item in value]
        raise ValueError("Invalid gpu_device_ids configuration")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
