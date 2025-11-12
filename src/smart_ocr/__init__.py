"""Smart OCR - 基于PaddleOCR的高并发OCR识别服务。

该包提供了一个完整的OCR服务实现，支持：
- 图像和PDF文件的文字识别
- 多GPU并行处理
- 高并发请求处理（支持10万级并发）
- RESTful API接口
- PDF票据检测与拆分
"""

from smart_ocr import pdf_ticket

__version__ = "1.0.0"

__all__ = ["pdf_ticket"]
