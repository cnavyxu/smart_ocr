# PDF票据处理器集成指南

本文档说明如何将 `PDFTicketProcessor` 集成到现有的OCR服务中。

## 概述

`PDFTicketProcessor` 是一个独立的票据处理模块，可以轻松集成到现有的 `smart_ocr` 服务中，用于处理包含多张票据的PDF文件。

## 基本集成步骤

### 1. 实现自定义检测器

根据业务需求实现票据检测器，检测器需要实现 `TicketDetector` 协议：

```python
from PIL import Image
from smart_ocr.pdf_ticket import BoundingBox, TicketDetectionResult

class MyTicketDetector:
    """自定义票据检测器。"""
    
    def detect(self, image: Image.Image, page_number: int = 1) -> TicketDetectionResult:
        """在图像中检测票据区域。
        
        参数:
            image: 待检测的PIL图像对象
            page_number: 页码
        
        返回:
            票据检测结果，包含所有检测到的边界框
        """
        # 实现检测逻辑
        # 例如：使用OpenCV轮廓检测、深度学习模型等
        
        boxes = []
        # ... 检测逻辑 ...
        
        # 返回检测结果
        return TicketDetectionResult(
            page_number=page_number,
            bounding_boxes=boxes,
        )
```

### 2. 在 orchestrator 中集成

在 `src/smart_ocr/orchestrator.py` 中添加票据处理功能：

```python
from pathlib import Path
from smart_ocr.pdf_ticket import (
    PDFTicketProcessor,
    PDFTicketProcessingError,
)
from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter

class Orchestrator:
    def __init__(self, ...):
        # 现有初始化代码...
        
        # 初始化票据处理器
        self.ticket_processor = PDFTicketProcessor(
            settings=self.settings,
            detector=MyTicketDetector(),  # 使用自定义检测器
            splitter=SimpleTicketSplitter(),
            save_to_disk=True,
        )
    
    async def process_pdf_with_tickets(
        self,
        pdf_bytes: bytes,
        output_dir: Path,
    ):
        """处理PDF文件并拆分票据。
        
        参数:
            pdf_bytes: PDF文件的字节流
            output_dir: 输出目录
        
        返回:
            拆分结果列表
        """
        try:
            # 使用票据处理器拆分PDF
            results = self.ticket_processor.process_pdf(
                pdf_source=pdf_bytes,
                output_dir=output_dir,
            )
            
            # 对每张票据进行OCR识别
            all_ocr_results = []
            
            for result in results:
                for ticket in result.tickets:
                    # 使用现有的OCR服务识别票据
                    ocr_result = await self._perform_ocr(ticket.image)
                    
                    # 添加票据元信息
                    ocr_result['page_number'] = ticket.page_number
                    ocr_result['ticket_index'] = ticket.ticket_index
                    ocr_result['saved_path'] = str(ticket.saved_path) if ticket.saved_path else None
                    
                    all_ocr_results.append(ocr_result)
            
            return {
                'total_pages': len(results),
                'total_tickets': sum(r.ticket_count for r in results),
                'tickets': all_ocr_results,
            }
            
        except PDFTicketProcessingError as e:
            logger.error(f"票据处理失败: {e}, 阶段: {e.stage}")
            raise
```

### 3. 在 API 端点中使用

在 `src/smart_ocr/app.py` 中添加新的API端点：

```python
@app.post("/v1/ocr/tickets")
async def ocr_tickets(
    request: OCRRequest,
    track_progress: bool = False,
):
    """处理包含多张票据的PDF，自动拆分并识别。
    
    该接口会自动检测PDF中的票据区域，拆分后逐张进行OCR识别。
    """
    # 验证输入
    if not (request.pdf_url or request.pdf_base64):
        raise HTTPException(
            status_code=400,
            detail="必须提供pdf_url或pdf_base64"
        )
    
    # 获取PDF字节流
    if request.pdf_url:
        pdf_bytes = await fetch_pdf(request.pdf_url)
    else:
        pdf_bytes = base64.b64decode(request.pdf_base64)
    
    # 准备输出目录
    output_dir = Path(f"/tmp/tickets/{uuid.uuid4()}")
    
    # 处理票据
    try:
        result = await orchestrator.process_pdf_with_tickets(
            pdf_bytes=pdf_bytes,
            output_dir=output_dir,
        )
        return result
    except PDFTicketProcessingError as e:
        raise HTTPException(
            status_code=500,
            detail=f"票据处理失败: {str(e)}"
        )
```

## 高级配置

### 使用组合检测器

如果需要使用多种检测策略：

```python
from smart_ocr.pdf_ticket import CompositeDetector

detector1 = ContourDetector()  # 基于轮廓的检测
detector2 = MLDetector()       # 基于机器学习的检测

composite = CompositeDetector([detector1, detector2])

processor = PDFTicketProcessor(
    settings=settings,
    detector=composite,
    splitter=splitter,
)
```

### 只检测不保存

如果只需要检测结果而不需要保存文件：

```python
processor = PDFTicketProcessor(
    settings=settings,
    detector=detector,
    splitter=splitter,
    save_to_disk=False,  # 不保存到磁盘
)

results = processor.process_pdf(pdf_bytes)

# 直接使用内存中的图像进行OCR
for result in results:
    for ticket in result.tickets:
        ocr_result = await ocr_service.recognize(ticket.image)
```

### 调试模式

开发阶段可以启用调试模式：

```python
processor = PDFTicketProcessor(
    settings=settings,
    detector=detector,
    splitter=splitter,
    debug_mode=True,  # 启用详细日志
)
```

## 配置项

相关的环境变量配置：

```bash
# PDF渲染DPI（影响图像质量和检测精度）
export SMART_OCR_PDF_RENDER_DPI=220

# GPU设备（如果检测器需要GPU）
export SMART_OCR_GPU_DEVICE_IDS=0,1,2
```

## 错误处理

统一的异常处理：

```python
from smart_ocr.pdf_ticket import PDFTicketProcessingError

try:
    results = processor.process_pdf(pdf_bytes, output_dir=output_dir)
except PDFTicketProcessingError as e:
    # 根据阶段进行不同的处理
    if e.stage == "loading":
        logger.error(f"PDF加载失败: {e.message}")
    elif e.stage == "detection":
        logger.error(f"票据检测失败: {e.message}")
    elif e.stage == "splitting":
        logger.error(f"票据拆分失败: {e.message}")
    
    # 访问原始异常
    logger.debug(f"原始错误: {e.original_error}")
```

## 性能优化建议

1. **DPI设置**: 根据票据大小和检测精度要求调整DPI（150-300）
2. **批处理**: 对于大量PDF，考虑使用异步批处理
3. **缓存**: 对相同PDF的重复请求，可以缓存检测结果
4. **GPU加速**: 如果检测器使用深度学习模型，确保启用GPU加速

## 示例：完整的票据OCR流程

```python
import asyncio
from pathlib import Path
from smart_ocr.config import get_settings
from smart_ocr.pdf_ticket import PDFTicketProcessor
from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter

async def process_ticket_pdf(pdf_path: str):
    """完整的票据处理流程示例。"""
    
    settings = get_settings()
    
    # 创建处理器
    processor = PDFTicketProcessor(
        settings=settings,
        detector=MyTicketDetector(),
        splitter=SimpleTicketSplitter(),
        save_to_disk=True,
    )
    
    # 处理PDF
    output_dir = Path("./output/tickets")
    results = processor.process_pdf(pdf_path, output_dir=output_dir)
    
    # 统计信息
    print(f"处理完成:")
    print(f"  - 总页数: {len(results)}")
    print(f"  - 总票据数: {sum(r.ticket_count for r in results)}")
    
    # 对每张票据进行OCR
    for result in results:
        for ticket in result.tickets:
            print(f"\n处理第{ticket.page_number}页的票据{ticket.ticket_index}...")
            print(f"  图像尺寸: {ticket.image.width}x{ticket.image.height}")
            print(f"  保存路径: {ticket.saved_path}")
            
            # 在这里调用OCR服务
            # ocr_result = await ocr_service.recognize(ticket.image)
            # print(f"  识别结果: {ocr_result}")

# 运行示例
if __name__ == "__main__":
    asyncio.run(process_ticket_pdf("document.pdf"))
```

## 测试

运行票据处理器的测试：

```bash
# 运行单元测试
pytest tests/pdf_ticket/test_pdf_ticket_processor.py -v

# 运行演示脚本
python test_ticket_processor_demo.py
```

## 下一步

1. 实现适合业务场景的检测器
2. 根据票据类型优化检测参数
3. 集成到现有的OCR流程中
4. 添加性能监控和日志记录
5. 编写集成测试

## 参考文档

- [PDF票据处理模块文档](src/smart_ocr/pdf_ticket/README.md)
- [测试示例](tests/pdf_ticket/test_pdf_ticket_processor.py)
- [演示脚本](test_ticket_processor_demo.py)
