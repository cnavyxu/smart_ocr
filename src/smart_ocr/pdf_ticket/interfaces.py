"""PDF票据处理的接口定义。

本模块定义票据检测器和拆分器的协议接口，便于依赖注入和扩展。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Protocol

from PIL import Image

from .models import BoundingBox, TicketDetectionResult, TicketImage, TicketSplitResult


class TicketDetector(Protocol):
    """票据检测器协议接口。
    
    实现该协议的类应提供detect方法，用于在图像中检测票据区域。
    """
    
    def detect(self, image: Image.Image, page_number: int = 1) -> TicketDetectionResult:
        """在图像中检测票据区域。
        
        参数:
            image: 待检测的PIL图像对象
            page_number: 页码（用于结果标识）
        
        返回:
            票据检测结果，包含所有检测到的边界框
        
        异常:
            Exception: 检测过程中的任何错误
        """
        ...


class TicketSplitter(Protocol):
    """票据拆分器协议接口。
    
    实现该协议的类应提供split方法，用于根据检测结果裁剪并保存票据图像。
    """
    
    def split(
        self,
        image: Image.Image,
        bounding_boxes: List[BoundingBox],
        page_number: int = 1,
        output_dir: Optional[Path] = None,
        save_to_disk: bool = True,
    ) -> TicketSplitResult:
        """根据边界框拆分票据图像。
        
        参数:
            image: 原始页面图像
            bounding_boxes: 票据边界框列表
            page_number: 页码
            output_dir: 输出目录，save_to_disk为True时必需
            save_to_disk: 是否保存到磁盘
        
        返回:
            票据拆分结果，包含所有拆分出的票据图像
        
        异常:
            Exception: 拆分或保存过程中的任何错误
        """
        ...


class PDFLoader(Protocol):
    """PDF加载器协议接口。
    
    实现该协议的类应提供load方法，用于将PDF转换为图像列表。
    """
    
    def load(self, pdf_source: str | bytes | Path, dpi: Optional[int] = None) -> List[Image.Image]:
        """加载PDF并转换为图像列表。
        
        参数:
            pdf_source: PDF数据源（文件路径或字节流）
            dpi: 渲染DPI分辨率
        
        返回:
            PIL图像对象列表
        
        异常:
            Exception: 加载或转换过程中的任何错误
        """
        ...
