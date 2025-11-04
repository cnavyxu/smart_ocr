from __future__ import annotations

"""OCR服务的所有请求与响应数据模型定义。"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """任务执行状态枚举。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRRequest(BaseModel):
    """OCR接口的请求数据模型。

    客户端可以通过三种方式提交待识别内容：
    1. 提供图像URL地址（image_url）
    2. 提供Base64编码的图像数据（image_base64）
    3. 提供PDF文件URL地址（pdf_url）或Base64编码的PDF数据（pdf_base64）

    注意：以上参数至少提供一项，否则请求会被拒绝。
    """

    image_url: Optional[str] = Field(
        default=None, description="待处理的图像文件URL地址"
    )
    image_base64: Optional[str] = Field(
        default=None, description="经过Base64编码后的图像二进制数据"
    )
    pdf_url: Optional[str] = Field(default=None, description="待处理的PDF文件URL地址")
    pdf_base64: Optional[str] = Field(
        default=None, description="经过Base64编码后的PDF二进制数据"
    )

    @validator("image_url", "image_base64", "pdf_url", "pdf_base64", pre=True, always=True)
    def _sanitize_empty_strings(cls, value: Optional[str]) -> Optional[str]:
        """将空字符串统一转换为None，避免误判。"""

        if isinstance(value, str) and not value.strip():
            return None
        return value

    @validator("pdf_base64", always=True)
    def _ensure_payload_provided(cls, value, values):
        """确保至少提供一种有效的输入数据来源。"""

        candidates = [
            values.get("image_url"),
            values.get("image_base64"),
            values.get("pdf_url"),
            value,
        ]
        if not any(candidates):
            raise ValueError(
                "必须提供以下参数之一: image_url, image_base64, pdf_url, pdf_base64"
            )
        return value


class TextPosition(BaseModel):
    """检测到的文本区域的边界框坐标。

    采用四个顶点的方式表示文本区域在原始图像中的位置，
    坐标系从图像左上角开始，单位为像素。
    """

    top_left: List[float] = Field(description="左上角顶点坐标 [x, y]")
    top_right: List[float] = Field(description="右上角顶点坐标 [x, y]")
    bottom_right: List[float] = Field(description="右下角顶点坐标 [x, y]")
    bottom_left: List[float] = Field(description="左下角顶点坐标 [x, y]")


class OCRTextResult(BaseModel):
    """单个文本区域的识别结果。

    包含识别出的文本内容、可信度分数以及该文本在图像中的位置信息。
    """

    text: str = Field(description="识别出的文本内容")
    confidence: float = Field(description="识别结果的置信度分数 (0-1)")
    position: TextPosition = Field(description="文本区域的四角坐标")
    page: Optional[int] = Field(default=None, description="对于PDF文件，表示文本所在的页码（从1开始）")


class OCRResponse(BaseModel):
    """OCR接口的响应数据模型。

    包含所有识别结果、统计信息和性能指标。
    """

    results: List[OCRTextResult] = Field(description="所有检测到的文本区域列表")
    text_count: int = Field(description="识别到的文本区域总数")
    processing_time: float = Field(description="OCR推理所消耗的时间（秒）")
    duration_ms: float = Field(description="整个请求的端到端处理时长（毫秒）")
    page_count: Optional[int] = Field(
        default=None, description="对于PDF文件，表示总页数"
    )
    task_id: Optional[str] = Field(
        default=None, description="任务唯一标识符，用于查询处理进度"
    )


class HealthResponse(BaseModel):
    """健康检查接口的响应模型。

    用于监控服务运行状态、版本信息和可用资源情况。
    """

    status: str = Field(description="服务运行状态标识，如 'healthy' 或 'unhealthy'")
    version: str = Field(description="当前运行的服务版本号")
    gpu_count: int = Field(description="系统配置使用的GPU设备数量")


class TaskProgressResponse(BaseModel):
    """任务进度查询的响应模型。"""

    task_id: str = Field(description="任务唯一标识符")
    status: TaskStatus = Field(description="任务当前状态")
    progress: float = Field(description="任务完成进度百分比 (0-100)")
    total_pages: int = Field(description="总页数")
    processed_pages: int = Field(description="已处理页数")
    start_time: float = Field(description="任务开始时间戳")
    end_time: Optional[float] = Field(default=None, description="任务结束时间戳")
    elapsed_time: float = Field(description="任务已经运行的时间（秒）")
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务完成后的结果")
    error: Optional[str] = Field(default=None, description="任务失败时的错误信息")


class TaskStatisticsResponse(BaseModel):
    """任务统计信息响应模型。"""

    total_tasks: int = Field(description="总任务数")
    pending: int = Field(description="等待中的任务数")
    processing: int = Field(description="处理中的任务数")
    completed: int = Field(description="已完成的任务数")
    failed: int = Field(description="失败的任务数")
    success_rate: float = Field(description="任务成功率百分比")


class TaskListResponse(BaseModel):
    """任务列表响应模型。"""

    tasks: List[TaskProgressResponse] = Field(description="任务信息列表")
    count: int = Field(description="返回的任务数量")
