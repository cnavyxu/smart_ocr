"""PDF票据处理模块。

提供PDF加载、票据检测与拆分功能。
"""

from .exceptions import PDFTicketProcessingError
from .interfaces import PDFLoader, TicketDetector, TicketSplitter
from .models import (
    BoundingBox,
    TicketDetectionResult,
    TicketImage,
    TicketSplitResult,
)
from .pdf_loader import (
    PDFLoadError,
    PageImage,
    load_pdf_from_bytes,
    load_pdf_from_path,
    load_pdf_to_images,
)
from .pdf_ticket_processor import (
    CompositeDetector,
    DefaultPDFLoader,
    PDFTicketProcessor,
)

__all__ = [
    # PDF加载
    "PDFLoadError",
    "PageImage",
    "load_pdf_from_bytes",
    "load_pdf_from_path",
    "load_pdf_to_images",
    # 票据处理
    "PDFTicketProcessor",
    "DefaultPDFLoader",
    "CompositeDetector",
    # 数据模型
    "BoundingBox",
    "TicketDetectionResult",
    "TicketImage",
    "TicketSplitResult",
    # 接口
    "PDFLoader",
    "TicketDetector",
    "TicketSplitter",
    # 异常
    "PDFTicketProcessingError",
]
