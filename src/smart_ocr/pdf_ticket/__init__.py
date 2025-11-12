"""PDF票据处理模块。

本模块提供票据检测、提取和处理功能，支持从PDF文件或图像中
识别和提取票据区域。
"""

from .ticket_detector import (
    BaseTicketDetector,
    CompositeTicketDetector,
    ContourTicketDetector,
    OCRTextTicketDetector,
    PageImage,
    TicketBoundingBox,
    TicketDetectionError,
)

__all__ = [
    "BaseTicketDetector",
    "CompositeTicketDetector",
    "ContourTicketDetector",
    "OCRTextTicketDetector",
    "PageImage",
    "TicketBoundingBox",
    "TicketDetectionError",
]
