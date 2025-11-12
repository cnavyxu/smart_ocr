"""票据分割模块的数据模型定义。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


class TicketSplitError(Exception):
    """票据分割过程中的自定义异常。
    
    用于封装文件IO错误、图像处理错误等所有与票据分割相关的异常。
    """
    
    pass


@dataclass
class PageImage:
    """表示PDF页面的图像数据。
    
    Attributes:
        image: PIL图像对象，包含页面的像素数据
        page_number: 页码，从1开始
        pdf_name: PDF文件名（不含扩展名），用于组织输出目录结构
        width: 图像宽度（像素）
        height: 图像高度（像素）
    """
    
    image: Image.Image
    page_number: int
    pdf_name: str
    width: int
    height: int
    
    @classmethod
    def from_image(
        cls,
        image: Image.Image,
        page_number: int,
        pdf_name: str,
    ) -> PageImage:
        """从PIL图像创建PageImage实例。
        
        Args:
            image: PIL图像对象
            page_number: 页码，从1开始
            pdf_name: PDF文件名（不含扩展名）
        
        Returns:
            PageImage实例
        """
        width, height = image.size
        return cls(
            image=image,
            page_number=page_number,
            pdf_name=pdf_name,
            width=width,
            height=height,
        )


@dataclass
class TicketBoundingBox:
    """表示检测到的票据边界框。
    
    Attributes:
        x1: 左上角x坐标（像素）
        y1: 左上角y坐标（像素）
        x2: 右下角x坐标（像素）
        y2: 右下角y坐标（像素）
        confidence: 检测置信度，取值范围[0, 1]
        strategy: 检测策略名称（例如："rule_based", "model_based"等）
    """
    
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float = 1.0
    strategy: str = "unknown"
    
    def get_width(self) -> int:
        """获取边界框的宽度。
        
        Returns:
            边界框宽度（像素）
        """
        return self.x2 - self.x1
    
    def get_height(self) -> int:
        """获取边界框的高度。
        
        Returns:
            边界框高度（像素）
        """
        return self.y2 - self.y1
    
    def expand_with_padding(
        self,
        padding: int,
        image_width: int,
        image_height: int,
    ) -> TicketBoundingBox:
        """扩展边界框并处理越界情况。
        
        在边界框四周添加padding像素，如果超出图像边界则自动裁剪到图像范围内。
        
        Args:
            padding: 要添加的padding像素数
            image_width: 图像宽度，用于边界检查
            image_height: 图像高度，用于边界检查
        
        Returns:
            扩展后的新TicketBoundingBox实例
        """
        new_x1 = max(0, self.x1 - padding)
        new_y1 = max(0, self.y1 - padding)
        new_x2 = min(image_width, self.x2 + padding)
        new_y2 = min(image_height, self.y2 + padding)
        
        return TicketBoundingBox(
            x1=new_x1,
            y1=new_y1,
            x2=new_x2,
            y2=new_y2,
            confidence=self.confidence,
            strategy=self.strategy,
        )


@dataclass
class TicketSplitResult:
    """表示单个票据分割的结果。
    
    Attributes:
        file_path: 保存的票据图像文件路径
        page_number: 来源页码，从1开始
        ticket_index: 票据在该页面中的索引，从0开始
        bounding_box: 票据的边界框信息
        strategy: 使用的检测策略名称
        width: 裁剪后图像的宽度（像素）
        height: 裁剪后图像的高度（像素）
        image_bytes: 可选的图像二进制数据（用于API直接返回）
    """
    
    file_path: Optional[Path]
    page_number: int
    ticket_index: int
    bounding_box: TicketBoundingBox
    strategy: str
    width: int
    height: int
    image_bytes: Optional[bytes] = None
    
    def to_dict(self) -> dict:
        """将结果转换为字典格式。
        
        Returns:
            包含所有字段的字典，文件路径转换为字符串
        """
        return {
            "file_path": str(self.file_path) if self.file_path else None,
            "page_number": self.page_number,
            "ticket_index": self.ticket_index,
            "bounding_box": {
                "x1": self.bounding_box.x1,
                "y1": self.bounding_box.y1,
                "x2": self.bounding_box.x2,
                "y2": self.bounding_box.y2,
                "confidence": self.bounding_box.confidence,
                "strategy": self.bounding_box.strategy,
            },
            "strategy": self.strategy,
            "width": self.width,
            "height": self.height,
            "has_image_bytes": self.image_bytes is not None,
        }
