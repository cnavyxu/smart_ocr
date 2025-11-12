from __future__ import annotations

"""PDF票据检测与拆分的数据模型定义。

该模块定义了票据处理流程中使用的核心数据结构，包括：
- 页面图像及其元数据
- 票据边界框信息
- 票据拆分结果记录
"""

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, validator


class PageImage(BaseModel):
    """PDF页转换后的图像及元数据。

    描述从PDF页面渲染得到的图像信息，包括页码、图像尺寸和渲染DPI等元数据。
    该模型用于在票据检测流程中传递页面图像数据及其上下文信息。

    Attributes:
        page_number: PDF页码，从1开始计数
        width: 图像宽度（像素）
        height: 图像高度（像素）
        dpi: 渲染时使用的DPI分辨率
        image_data: 图像的NumPy数组表示或文件路径（可选）
    """

    page_number: int = Field(ge=1, description="PDF页码（从1开始）")
    width: int = Field(gt=0, description="图像宽度（像素）")
    height: int = Field(gt=0, description="图像高度（像素）")
    dpi: int = Field(gt=0, description="渲染DPI分辨率")
    image_data: Optional[str] = Field(
        default=None, description="图像数据的文件路径或标识符"
    )

    class Config:
        """Pydantic配置项。"""

        arbitrary_types_allowed = True


class TicketBoundingBox(BaseModel):
    """统一的票据检测边界框模型。

    表示通过各种检测策略（OCR、轮廓检测等）识别出的票据区域边界框。
    边界框使用左上角和右下角坐标表示，并记录检测置信度和来源策略。

    Attributes:
        x1: 边界框左上角X坐标（像素）
        y1: 边界框左上角Y坐标（像素）
        x2: 边界框右下角X坐标（像素）
        y2: 边界框右下角Y坐标（像素）
        confidence: 检测置信度分数（0-1范围）
        source_strategy: 检测来源策略，可选值为 'ocr' 或 'contour'
        page_number: 票据所在的PDF页码（从1开始）
    """

    x1: float = Field(ge=0, description="边界框左上角X坐标（像素）")
    y1: float = Field(ge=0, description="边界框左上角Y坐标（像素）")
    x2: float = Field(ge=0, description="边界框右下角X坐标（像素）")
    y2: float = Field(ge=0, description="边界框右下角Y坐标（像素）")
    confidence: float = Field(
        ge=0.0, le=1.0, description="检测置信度分数（0-1范围）"
    )
    source_strategy: Literal["ocr", "contour"] = Field(
        description="检测来源策略：'ocr'表示基于OCR检测，'contour'表示基于轮廓检测"
    )
    page_number: int = Field(ge=1, description="票据所在的PDF页码（从1开始）")

    @validator("x2")
    def _validate_x2_greater_than_x1(cls, value: float, values: dict) -> float:
        """确保右下角X坐标大于左上角X坐标。"""
        if "x1" in values and value <= values["x1"]:
            raise ValueError("x2必须大于x1")
        return value

    @validator("y2")
    def _validate_y2_greater_than_y1(cls, value: float, values: dict) -> float:
        """确保右下角Y坐标大于左上角Y坐标。"""
        if "y1" in values and value <= values["y1"]:
            raise ValueError("y2必须大于y1")
        return value

    def get_area(self) -> float:
        """计算边界框的面积（平方像素）。

        Returns:
            边界框面积（宽度 × 高度）
        """
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def get_dimensions(self) -> Tuple[float, float]:
        """获取边界框的宽度和高度。

        Returns:
            (宽度, 高度) 元组
        """
        return (self.x2 - self.x1, self.y2 - self.y1)


class TicketSplitResult(BaseModel):
    """票据拆分结果记录。

    记录从PDF中拆分出的单个票据图像信息，包括保存路径、索引编号和来源页码等。

    Attributes:
        output_path: 拆分后票据图像的保存文件路径
        ticket_index: 票据在整个PDF中的索引编号（从0开始）
        source_page: 票据的来源PDF页码（从1开始）
        bounding_box: 原始边界框信息（可选）
        width: 拆分图像的宽度（像素）
        height: 拆分图像的高度（像素）
    """

    output_path: str = Field(description="拆分后票据图像的保存文件路径")
    ticket_index: int = Field(ge=0, description="票据索引编号（从0开始）")
    source_page: int = Field(ge=1, description="来源PDF页码（从1开始）")
    bounding_box: Optional[TicketBoundingBox] = Field(
        default=None, description="原始边界框信息"
    )
    width: int = Field(gt=0, description="拆分图像的宽度（像素）")
    height: int = Field(gt=0, description="拆分图像的高度（像素）")

    @validator("output_path")
    def _validate_output_path(cls, value: str) -> str:
        """验证输出路径非空且格式正确。"""
        if not value or not value.strip():
            raise ValueError("output_path不能为空")
        return value.strip()
