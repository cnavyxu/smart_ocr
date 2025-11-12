"""PDF票据处理相关的数据模型定义。

本模块定义票据检测、拆分过程中使用的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image


@dataclass
class BoundingBox:
    """票据边界框。
    
    表示在图像中检测到的票据区域的矩形边界。
    
    属性:
        x: 边界框左上角的x坐标（像素）
        y: 边界框左上角的y坐标（像素）
        width: 边界框宽度（像素）
        height: 边界框高度（像素）
        confidence: 检测置信度分数（0-1），可选
    """
    
    x: int
    y: int
    width: int
    height: int
    confidence: Optional[float] = None
    
    def to_coordinates(self) -> Tuple[int, int, int, int]:
        """转换为(x1, y1, x2, y2)坐标格式。
        
        返回:
            包含左上角和右下角坐标的元组 (x1, y1, x2, y2)
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    @property
    def area(self) -> int:
        """计算边界框面积。
        
        返回:
            边界框的面积（像素）
        """
        return self.width * self.height


@dataclass
class TicketDetectionResult:
    """单页图像的票据检测结果。
    
    属性:
        page_number: 页码（从1开始）
        bounding_boxes: 检测到的票据边界框列表
        detection_time: 检测耗时（秒），可选
    """
    
    page_number: int
    bounding_boxes: List[BoundingBox]
    detection_time: Optional[float] = None
    
    @property
    def ticket_count(self) -> int:
        """返回检测到的票据数量。"""
        return len(self.bounding_boxes)


@dataclass
class TicketImage:
    """拆分后的单张票据图像。
    
    属性:
        image: PIL图像对象
        bbox: 原始边界框信息
        page_number: 来源页码
        ticket_index: 在该页中的票据索引（从0开始）
        saved_path: 保存的文件路径，可选
    """
    
    image: Image.Image
    bbox: BoundingBox
    page_number: int
    ticket_index: int
    saved_path: Optional[Path] = None


@dataclass
class TicketSplitResult:
    """票据拆分结果。
    
    包含从PDF单页中拆分出的所有票据图像及相关信息。
    
    属性:
        page_number: 页码（从1开始）
        tickets: 拆分出的票据图像列表
        split_time: 拆分耗时（秒），可选
    """
    
    page_number: int
    tickets: List[TicketImage]
    split_time: Optional[float] = None
    
    @property
    def ticket_count(self) -> int:
        """返回拆分出的票据数量。"""
        return len(self.tickets)
