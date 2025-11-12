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

## 示例

完整示例请参考 `test_pdf_loader_demo.py` 脚本。
