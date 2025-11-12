"""PDF票据检测与拆分模块。

该模块提供票据检测、边界框定位和票据拆分的核心功能，
支持基于OCR和轮廓检测两种策略，为票据处理流程奠定基础。
"""

from smart_ocr.pdf_ticket.models import (
    PageImage,
    TicketBoundingBox,
    TicketSplitResult,
)

__all__ = [
    "PageImage",
    "TicketBoundingBox",
    "TicketSplitResult",
]
