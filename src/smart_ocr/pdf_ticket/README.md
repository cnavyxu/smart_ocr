# PDF票据处理模块

提供PDF加载、票据检测与拆分功能，用于将多页PDF转换为高质量图像供后续处理。

## 功能特性

- ✅ 支持从文件路径或字节流加载PDF
- ✅ 使用PyMuPDF将每页渲染为指定DPI的图像
- ✅ 支持PNG和JPEG输出格式
- ✅ 记录完整的页面元信息（页码、尺寸、DPI等）
- ✅ 统一的异常处理机制
- ✅ 可选的调试保存功能

## 快速开始

### 基本用法

```python
from smart_ocr.pdf_ticket import load_pdf_to_images

# 从字节流加载
with open("document.pdf", "rb") as f:
    pdf_bytes = f.read()

pages = load_pdf_to_images(pdf_bytes)
print(f"共加载 {len(pages)} 页")

# 访问页面信息
for page in pages:
    print(f"第{page.page_number}页: {page.width}x{page.height}px, DPI={page.dpi}")
```

### 从文件路径加载

```python
from smart_ocr.pdf_ticket import load_pdf_from_path

pages = load_pdf_from_path("document.pdf")
```

### 自定义参数

```python
# 指定DPI和输出格式
pages = load_pdf_to_images(
    pdf_bytes,
    dpi=300,              # 更高的分辨率
    output_format="JPEG"  # 使用JPEG格式
)

# 保存渲染结果用于调试
pages = load_pdf_to_images(
    pdf_bytes,
    save_to_disk=True,
    save_dir="./output"
)
# 将在./output目录下生成 page_1.png, page_2.png 等文件
```

## API文档

### load_pdf_to_images

主要的API函数，支持从文件路径或字节流加载PDF。

**参数：**
- `pdf_source`: PDF数据源，可以是文件路径（str或Path）或字节流（bytes）
- `dpi`: 渲染分辨率（DPI），默认从配置读取（220）
- `output_format`: 输出图像格式，支持 'PNG' 或 'JPEG'，默认 'PNG'
- `save_to_disk`: 是否将渲染后的图像保存到磁盘（用于调试），默认False
- `save_dir`: 保存目录路径

**返回：**
- `List[PageImage]`: PageImage对象列表

**异常：**
- `PDFLoadError`: PDF加载、解析或渲染失败时抛出
- `ValueError`: 参数格式不正确时抛出

### load_pdf_from_path

从文件路径加载PDF。

**参数：** 同 `load_pdf_to_images`（除了 `pdf_source` 改为 `pdf_path`）

### load_pdf_from_bytes

从字节流加载PDF。

**参数：** 同 `load_pdf_to_images`（除了 `pdf_source` 改为 `pdf_bytes`）

### PageImage 数据类

包含单页PDF渲染后的图像及其元信息。

**属性：**
- `page_number`: 页码（从1开始）
- `image`: PIL图像对象
- `image_bytes`: 图像的二进制数据（PNG或JPEG格式）
- `width`: 图像宽度（像素）
- `height`: 图像高度（像素）
- `dpi`: 渲染时使用的DPI分辨率
- `format`: 图像输出格式（'PNG' 或 'JPEG'）

### PDFLoadError 异常

PDF加载和处理过程中的自定义异常类。

## 配置

默认DPI可以通过环境变量 `SMART_OCR_PDF_RENDER_DPI` 配置：

```bash
export SMART_OCR_PDF_RENDER_DPI=300
```

或在代码中指定：

```python
pages = load_pdf_to_images(pdf_bytes, dpi=300)
```

## 性能优化

1. **上下文管理器**: 使用PyMuPDF的上下文管理器，确保文档对象正确关闭
2. **矩阵放缩**: 使用变换矩阵实现高效的DPI调整
3. **批量渲染**: 在单次打开文档中渲染所有页面，避免重复开闭

## 异常处理

所有内部异常都会被统一转换为 `PDFLoadError`，便于上层调用者捕获和处理：

```python
from smart_ocr.pdf_ticket import load_pdf_to_images, PDFLoadError

try:
    pages = load_pdf_to_images(pdf_bytes)
except PDFLoadError as e:
    print(f"PDF加载失败: {e}")
    # 进行错误处理
```

常见错误场景：
- 空字节流
- 损坏的PDF文件
- 文件不存在
- 无法渲染的页面

## 测试

运行单元测试：

```bash
pytest tests/pdf_ticket/test_pdf_loader.py -v
```

运行演示脚本：

```bash
python test_pdf_loader_demo.py
```

## 依赖

- PyMuPDF (fitz): PDF解析和渲染
- Pillow (PIL): 图像处理
- Pydantic: 配置管理

## PDF票据处理器 (PDFTicketProcessor)

### 概述

`PDFTicketProcessor` 是一个主控模块，协调PDF加载、票据检测与拆分的完整流程。它支持依赖注入，可以灵活配置自定义的检测器和拆分器。

### 快速开始

```python
from smart_ocr.config import get_settings
from smart_ocr.pdf_ticket import PDFTicketProcessor
from pathlib import Path

# 准备配置
settings = get_settings()

# 实现自定义检测器
class MyDetector:
    def detect(self, image, page_number=1):
        from smart_ocr.pdf_ticket import BoundingBox, TicketDetectionResult
        # 实现检测逻辑，返回边界框列表
        boxes = [
            BoundingBox(x=10, y=10, width=200, height=150, confidence=0.95),
            # ...更多边界框
        ]
        return TicketDetectionResult(
            page_number=page_number,
            bounding_boxes=boxes
        )

# 使用内置的简单拆分器
from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter

# 创建处理器
processor = PDFTicketProcessor(
    settings=settings,
    detector=MyDetector(),
    splitter=SimpleTicketSplitter(),
    save_to_disk=True,
)

# 处理PDF
results = processor.process_pdf(
    "document.pdf",
    output_dir=Path("./output")
)

# 查看结果
print(f"共处理 {len(results)} 页")
for result in results:
    print(f"第{result.page_number}页: 拆分出{result.ticket_count}张票据")
    for ticket in result.tickets:
        print(f"  -> 保存位置: {ticket.saved_path}")
```

### 核心组件

#### PDFTicketProcessor

主处理器类，协调整个流程。

**构造参数：**
- `settings`: Settings配置对象
- `detector`: 票据检测器实例（可选，也可在调用时提供）
- `splitter`: 票据拆分器实例（可选，也可在调用时提供）
- `pdf_loader`: PDF加载器实例（可选，默认使用内置实现）
- `save_to_disk`: 是否保存拆分结果到磁盘（默认True）
- `debug_mode`: 是否启用调试模式（默认False）

**主要方法：**

```python
def process_pdf(
    pdf_source: Union[str, bytes, Path],
    output_dir: Optional[Path] = None,
    detector: Optional[TicketDetector] = None,
    splitter: Optional[TicketSplitter] = None,
) -> List[TicketSplitResult]:
    """处理PDF文件，返回拆分结果列表。"""
```

#### 数据模型

**BoundingBox** - 票据边界框
```python
@dataclass
class BoundingBox:
    x: int              # 左上角x坐标
    y: int              # 左上角y坐标
    width: int          # 宽度
    height: int         # 高度
    confidence: float   # 置信度(可选)
```

**TicketSplitResult** - 拆分结果
```python
@dataclass
class TicketSplitResult:
    page_number: int              # 页码
    tickets: List[TicketImage]    # 拆分出的票据列表
    split_time: float             # 拆分耗时(可选)
```

**TicketImage** - 单张票据
```python
@dataclass
class TicketImage:
    image: Image.Image      # PIL图像对象
    bbox: BoundingBox       # 原始边界框
    page_number: int        # 来源页码
    ticket_index: int       # 在该页中的索引
    saved_path: Path        # 保存路径(可选)
```

### 接口定义

实现以下协议接口以自定义检测器和拆分器：

#### TicketDetector (检测器协议)

```python
class MyDetector:
    def detect(self, image: Image.Image, page_number: int = 1) -> TicketDetectionResult:
        """在图像中检测票据区域。
        
        参数:
            image: 待检测的PIL图像
            page_number: 页码
        
        返回:
            TicketDetectionResult对象
        """
        # 实现检测逻辑
        pass
```

#### TicketSplitter (拆分器协议)

```python
class MySplitter:
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
            output_dir: 输出目录
            save_to_disk: 是否保存到磁盘
        
        返回:
            TicketSplitResult对象
        """
        # 实现拆分逻辑
        pass
```

### 高级特性

#### 组合检测器

使用多个检测器组合处理：

```python
from smart_ocr.pdf_ticket import CompositeDetector

detector1 = ContourDetector()
detector2 = MLDetector()

composite = CompositeDetector([detector1, detector2])

processor = PDFTicketProcessor(
    settings=settings,
    detector=composite,  # 使用组合检测器
    splitter=splitter,
)
```

#### 只检测不保存

```python
processor = PDFTicketProcessor(
    settings=settings,
    detector=detector,
    splitter=splitter,
    save_to_disk=False,  # 不保存到磁盘
)

results = processor.process_pdf("document.pdf")

# 结果中包含图像对象，但未保存文件
for result in results:
    for ticket in result.tickets:
        # ticket.image 可用
        # ticket.saved_path 为 None
        pass
```

#### 调试模式

启用调试模式获取详细日志：

```python
processor = PDFTicketProcessor(
    settings=settings,
    detector=detector,
    splitter=splitter,
    debug_mode=True,  # 启用调试
)
```

#### 临时覆盖检测器/拆分器

```python
# 初始化时使用默认检测器
processor = PDFTicketProcessor(
    settings=settings,
    detector=default_detector,
    splitter=default_splitter,
)

# 处理时临时使用其他检测器
results = processor.process_pdf(
    "special.pdf",
    output_dir=Path("./output"),
    detector=special_detector,  # 临时覆盖
)
```

### 异常处理

所有异常都会被转换为 `PDFTicketProcessingError`：

```python
from smart_ocr.pdf_ticket import PDFTicketProcessingError

try:
    results = processor.process_pdf("document.pdf", output_dir=Path("./output"))
except PDFTicketProcessingError as e:
    print(f"处理失败: {e}")
    print(f"阶段: {e.stage}")  # loading, detection, splitting
    print(f"原始错误: {e.original_error}")
```

### 输出目录结构

默认的文件命名格式：

```
output/
├── page_1_ticket_0.png
├── page_1_ticket_1.png
├── page_2_ticket_0.png
└── page_2_ticket_1.png
```

格式: `page_{页码}_ticket_{索引}.{格式}`

### 配置项

通过环境变量或Settings配置：

- `SMART_OCR_PDF_RENDER_DPI`: PDF渲染DPI（默认220）

```python
# 通过代码设置
settings = Settings(pdf_render_dpi=300)

# 或通过环境变量
export SMART_OCR_PDF_RENDER_DPI=300
```

### 测试

运行票据处理器测试：

```bash
pytest tests/pdf_ticket/test_pdf_ticket_processor.py -v
```

### 内置实现

#### SimpleTicketSplitter

提供基本的图像裁剪和保存功能：

```python
from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter

splitter = SimpleTicketSplitter(image_format="PNG")  # 或 "JPEG"
```

### 与主流程集成

在现有的OCR服务中集成票据处理：

```python
# 在orchestrator或image_loader中使用
from smart_ocr.pdf_ticket import PDFTicketProcessor

async def process_pdf_with_tickets(pdf_bytes: bytes, settings: Settings):
    # 创建处理器
    processor = PDFTicketProcessor(
        settings=settings,
        detector=your_detector,
        splitter=your_splitter,
    )
    
    # 处理PDF
    results = processor.process_pdf(pdf_bytes, output_dir=output_path)
    
    # 对每张票据进行OCR
    for result in results:
        for ticket in result.tickets:
            ocr_result = await ocr_service.recognize(ticket.image)
            # 处理OCR结果
```

## 示例

完整示例请参考 `test_pdf_loader_demo.py` 脚本和 `tests/pdf_ticket/test_pdf_ticket_processor.py` 测试文件。
