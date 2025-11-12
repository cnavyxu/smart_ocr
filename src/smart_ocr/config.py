from __future__ import annotations

"""应用级配置项定义与加载逻辑。"""

import os
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

    # 票据检测与拆分相关配置
    ticket_detection_strategies: List[str] = Field(
        default_factory=lambda: ["ocr", "contour"],
        description="启用的票据检测策略列表，可选值：'ocr'（基于OCR文本检测）、'contour'（基于轮廓检测）",
    )
    ticket_allow_ocr_detection: bool = Field(
        default=True,
        description="是否允许使用OCR检测策略进行票据识别",
    )
    ticket_allow_contour_detection: bool = Field(
        default=True,
        description="是否允许使用轮廓检测策略进行票据识别",
    )
    ticket_detection_min_area: int = Field(
        default=10000,
        description="票据检测的最小面积阈值（平方像素），小于此值的区域将被过滤",
    )
    ticket_detection_min_text: int = Field(
        default=10,
        description="基于OCR检测时，票据区域应包含的最小文本字符数",
    )
    ticket_output_root: str = Field(
        default="./outputs/tickets",
        description="拆分后票据图像的输出根目录路径",
    )
    ticket_padding_pixels: int = Field(
        default=10,
        description="拆分票据图像时，在边界框四周添加的留白像素数",
    )

    class Config:
        """Pydantic配置项，指定环境变量前缀与匹配规则。"""

        env_prefix = "SMART_OCR_"
        case_sensitive = False

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """自定义环境变量解析器，处理特殊字段的解析逻辑。"""
            if field_name == "ticket_detection_strategies":
                # 对于策略列表，支持逗号分隔的字符串
                return raw_val
            # 对于其他字段，使用默认解析逻辑
            import json
            try:
                return json.loads(raw_val)
            except json.JSONDecodeError:
                return raw_val

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

    @validator("ticket_detection_strategies", pre=True)
    def _parse_detection_strategies(cls, value: object) -> List[str]:
        """将环境变量中的策略字符串解析为列表，并验证策略合法性。"""

        if value is None:
            return ["ocr", "contour"]
        if isinstance(value, str):
            strategies = [item.strip().lower() for item in value.split(",") if item.strip()]
        elif isinstance(value, (list, tuple)):
            strategies = [str(item).strip().lower() for item in value]
        else:
            raise ValueError("Invalid ticket_detection_strategies configuration")

        valid_strategies = {"ocr", "contour"}
        for strategy in strategies:
            if strategy not in valid_strategies:
                raise ValueError(
                    f"Invalid detection strategy: {strategy}. "
                    f"Valid strategies are: {', '.join(valid_strategies)}"
                )

        if not strategies:
            raise ValueError("At least one detection strategy must be enabled")

        return strategies

    @validator("ticket_output_root")
    def _validate_and_create_ticket_output_root(cls, value: str) -> str:
        """验证输出目录路径，并在不存在时自动创建。"""

        if not value or not value.strip():
            raise ValueError("ticket_output_root cannot be empty")

        value = value.strip()
        os.makedirs(value, exist_ok=True)
        return value

    @validator("ticket_detection_min_area")
    def _validate_min_area(cls, value: int) -> int:
        """验证最小面积阈值为正数。"""

        if value <= 0:
            raise ValueError("ticket_detection_min_area must be positive")
        return value

    @validator("ticket_detection_min_text")
    def _validate_min_text(cls, value: int) -> int:
        """验证最小文本字符数为非负数。"""

        if value < 0:
            raise ValueError("ticket_detection_min_text must be non-negative")
        return value

    @validator("ticket_padding_pixels")
    def _validate_padding(cls, value: int) -> int:
        """验证留白像素数为非负数。"""

        if value < 0:
            raise ValueError("ticket_padding_pixels must be non-negative")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回带缓存的全局配置实例，避免重复解析环境变量。"""

    return Settings()
