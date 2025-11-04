from __future__ import annotations

"""应用级配置项定义与加载逻辑。"""

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """应用程序的所有运行时配置项。

    该配置类会从环境变量中读取参数，并提供默认值以便在开发阶段快速启动。
    所有字段均提供详细的说明，方便在部署过程中根据业务场景进行调优。
    """

    app_name: str = Field(default="smart-ocr-service", description="服务实例名称")
    api_prefix: str = Field(default="/v1", description="所有API接口的统一前缀")
    gpu_device_ids: List[int] = Field(
        default_factory=lambda: [0, 1, 2],
        description="允许用于推理的GPU设备编号列表",
    )
    use_gpu: bool = Field(default=True, description="是否启用GPU模式运行PaddleOCR")
    paddle_lang: str = Field(default="ch", description="PaddleOCR使用的语言模型标识")
    max_queue_size: int = Field(
        default=100_000,
        description="请求并发队列的最大长度，防止系统过载",
    )
    max_workers: int = Field(
        default=32,
        description="HTTP层并发工作协程的数量上限",
    )
    fetch_timeout_seconds: float = Field(
        default=10.0,
        description="下载远程资源时的超时时间（秒）",
    )
    request_timeout_seconds: float = Field(
        default=25.0,
        description="FastAPI 接口处理请求的整体超时时间（秒）",
    )
    pdf_render_dpi: int = Field(
        default=220,
        description="将PDF页面渲染为图像时使用的DPI分辨率",
    )

    class Config:
        """Pydantic配置项，指定环境变量前缀与匹配规则。"""

        env_prefix = "SMART_OCR_"
        case_sensitive = False

    @validator("gpu_device_ids", pre=True)
    def _parse_gpu_ids(cls, value: object) -> List[int]:
        """将环境变量中的GPU编号字符串解析为整数列表。"""

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
    """返回带缓存的全局配置实例，避免重复解析环境变量。"""

    return Settings()
