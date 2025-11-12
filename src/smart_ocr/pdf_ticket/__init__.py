"""票据分割模块，用于从PDF页面中检测、裁剪和保存票据图像。"""

from smart_ocr.pdf_ticket.models import (
    PageImage,
    TicketBoundingBox,
    TicketSplitError,
    TicketSplitResult,
)
from smart_ocr.pdf_ticket.ticket_splitter import TicketSplitter

__all__ = [
    "PageImage",
    "TicketBoundingBox",
    "TicketSplitResult",
    "TicketSplitError",
    "TicketSplitter",
]
