# PDF票据分割模块

## 概述

本模块提供票据分割功能，可以根据检测到的边界框从PDF页面图像中裁剪并保存单个票据图像。

## 主要组件

### 数据模型 (`models.py`)

- **`PageImage`**: 表示PDF页面的图像数据
  - 包含PIL图像对象、页码、PDF名称和尺寸信息
  - 提供`from_image()`类方法用于便捷创建

- **`TicketBoundingBox`**: 表示票据边界框
  - 包含坐标(x1, y1, x2, y2)、置信度和检测策略
  - 提供`expand_with_padding()`方法支持边界扩展和越界处理

- **`TicketSplitResult`**: 表示分割结果
  - 包含文件路径、页码、票据索引、边界框、尺寸等元数据
  - 支持可选的图像字节数据（用于API返回）
  - 提供`to_dict()`方法用于序列化

- **`TicketSplitError`**: 自定义异常
  - 封装所有票据分割相关的错误

### 票据分割器 (`ticket_splitter.py`)

- **`TicketSplitter`**: 主要分割器类
  - 根据边界框裁剪图像
  - 支持可配置的padding
  - 保存到规范的目录结构
  - 支持磁盘保存和内存返回两种模式

## 使用示例

### 基本使用

```python
from pathlib import Path
from PIL import Image
from smart_ocr.config import Settings
from smart_ocr.pdf_ticket import (
    TicketSplitter,
    PageImage,
    TicketBoundingBox,
)

# 创建配置和分割器
settings = Settings()
splitter = TicketSplitter(
    settings=settings,
    output_root=Path("/output/tickets"),
    image_format="png",
    padding=10,  # 边界框周围添加10像素padding
)

# 准备页面图像
image = Image.open("page.png")
page = PageImage.from_image(image, page_number=1, pdf_name="invoice_001")

# 定义票据边界框
boxes = [
    TicketBoundingBox(100, 100, 300, 400, confidence=0.95, strategy="model"),
    TicketBoundingBox(400, 100, 600, 400, confidence=0.90, strategy="model"),
]

# 执行分割
results = splitter.split_page_tickets(page, boxes)

# 处理结果
for result in results:
    print(f"保存到: {result.file_path}")
    print(f"尺寸: {result.width}x{result.height}")
    print(f"置信度: {result.bounding_box.confidence}")
```

### 仅内存返回（用于API）

```python
# 创建不保存到磁盘的分割器
splitter = TicketSplitter(
    settings=settings,
    output_root=Path("/tmp"),  # 不会使用
    save_to_disk=False,
    return_bytes=True,
)

results = splitter.split_page_tickets(page, boxes)

# 获取图像字节数据
image_bytes = results[0].image_bytes
# 可以直接通过API返回
```

### 自定义格式和配置

```python
# 保存为JPG格式
splitter = TicketSplitter(
    settings=settings,
    output_root=Path("/output/tickets"),
    image_format="jpg",
    padding=20,
    save_to_disk=True,
    return_bytes=True,  # 同时保存文件和返回字节
)
```

## 输出目录结构

分割器会创建以下目录结构：

```
{output_root}/
  └── {pdf_name}/
      ├── page_1_ticket_0.png
      ├── page_1_ticket_1.png
      ├── page_2_ticket_0.png
      └── ...
```

## 命名规范

文件命名遵循格式：`page_{页码}_ticket_{索引}.{格式}`

- 页码从1开始
- 索引从0开始
- 格式可配置（默认png）

## 边界框Padding

`TicketBoundingBox.expand_with_padding()` 方法可以在边界框周围添加padding：

- 自动处理边界越界情况
- 不会超出图像范围
- 保持原始策略和置信度

## 异常处理

所有操作相关的异常都会被包装为 `TicketSplitError`：

- 目录创建失败
- 图像裁剪失败
- 文件保存失败
- 图像转换失败

```python
from smart_ocr.pdf_ticket import TicketSplitError

try:
    results = splitter.split_page_tickets(page, boxes)
except TicketSplitError as e:
    print(f"分割失败: {e}")
```

## 日志记录

模块使用标准的Python logging模块记录详细信息：

- INFO级别：保存的文件路径、分割统计
- DEBUG级别：裁剪细节、尺寸信息
- ERROR级别：错误信息

## 测试

运行单元测试：

```bash
pytest tests/pdf_ticket/test_ticket_splitter.py -v
```

测试覆盖：
- 文件名生成
- 边界框padding逻辑
- 图像裁剪正确性
- 目录结构创建
- 多种配置组合
- 异常处理
- 结果序列化
