# PDF票据检测与拆分配置文档

## 概述

本文档描述了 Smart OCR 服务中新增的 PDF 票据检测与拆分功能的配置项和数据模型。

## 配置项

所有配置项都可以通过环境变量设置，环境变量名需要加上 `SMART_OCR_` 前缀。

### 票据检测策略配置

#### `ticket_detection_strategies`
- **类型**: List[str]
- **默认值**: `["ocr", "contour"]`
- **说明**: 启用的票据检测策略列表
- **可选值**: 
  - `ocr`: 基于OCR文本检测的策略
  - `contour`: 基于轮廓检测的策略
- **环境变量**: `SMART_OCR_TICKET_DETECTION_STRATEGIES`
- **示例**: `SMART_OCR_TICKET_DETECTION_STRATEGIES=ocr,contour`

#### `ticket_allow_ocr_detection`
- **类型**: bool
- **默认值**: `True`
- **说明**: 是否允许使用OCR检测策略进行票据识别
- **环境变量**: `SMART_OCR_TICKET_ALLOW_OCR_DETECTION`

#### `ticket_allow_contour_detection`
- **类型**: bool
- **默认值**: `True`
- **说明**: 是否允许使用轮廓检测策略进行票据识别
- **环境变量**: `SMART_OCR_TICKET_ALLOW_CONTOUR_DETECTION`

### 票据检测阈值配置

#### `ticket_detection_min_area`
- **类型**: int
- **默认值**: `10000`
- **说明**: 票据检测的最小面积阈值（平方像素），小于此值的区域将被过滤
- **环境变量**: `SMART_OCR_TICKET_DETECTION_MIN_AREA`
- **约束**: 必须为正整数

#### `ticket_detection_min_text`
- **类型**: int
- **默认值**: `10`
- **说明**: 基于OCR检测时，票据区域应包含的最小文本字符数
- **环境变量**: `SMART_OCR_TICKET_DETECTION_MIN_TEXT`
- **约束**: 必须为非负整数

### 票据输出配置

#### `ticket_output_root`
- **类型**: str
- **默认值**: `"./outputs/tickets"`
- **说明**: 拆分后票据图像的输出根目录路径
- **环境变量**: `SMART_OCR_TICKET_OUTPUT_ROOT`
- **注意**: 目录不存在时会自动创建

#### `ticket_padding_pixels`
- **类型**: int
- **默认值**: `10`
- **说明**: 拆分票据图像时，在边界框四周添加的留白像素数
- **环境变量**: `SMART_OCR_TICKET_PADDING_PIXELS`
- **约束**: 必须为非负整数

## 数据模型

### PageImage

描述PDF页转换后的图像及元数据。

```python
from smart_ocr.pdf_ticket import PageImage

page = PageImage(
    page_number=1,       # PDF页码（从1开始）
    width=1920,          # 图像宽度（像素）
    height=1080,         # 图像高度（像素）
    dpi=220,             # 渲染DPI分辨率
    image_data=None      # 图像数据路径（可选）
)
```

### TicketBoundingBox

统一的票据检测边界框模型。

```python
from smart_ocr.pdf_ticket import TicketBoundingBox

bbox = TicketBoundingBox(
    x1=100.0,                    # 左上角X坐标
    y1=200.0,                    # 左上角Y坐标
    x2=800.0,                    # 右下角X坐标
    y2=900.0,                    # 右下角Y坐标
    confidence=0.95,             # 检测置信度（0-1）
    source_strategy="ocr",       # 检测策略：'ocr' 或 'contour'
    page_number=1                # 所在页码
)

# 辅助方法
area = bbox.get_area()                # 获取边界框面积
width, height = bbox.get_dimensions() # 获取宽度和高度
```

### TicketSplitResult

票据拆分结果记录。

```python
from smart_ocr.pdf_ticket import TicketSplitResult

result = TicketSplitResult(
    output_path="/output/ticket_0.png",  # 拆分后图像的保存路径
    ticket_index=0,                      # 票据索引（从0开始）
    source_page=1,                       # 来源页码（从1开始）
    bounding_box=bbox,                   # 边界框信息（可选）
    width=700,                           # 拆分图像宽度
    height=700                           # 拆分图像高度
)
```

## 使用示例

### 基本使用

```python
from smart_ocr.config import get_settings
from smart_ocr.pdf_ticket import PageImage, TicketBoundingBox, TicketSplitResult

# 获取配置
settings = get_settings()
print(f"检测策略: {settings.ticket_detection_strategies}")
print(f"输出目录: {settings.ticket_output_root}")

# 创建页面图像
page = PageImage(
    page_number=1,
    width=1920,
    height=1080,
    dpi=settings.pdf_render_dpi
)

# 创建边界框
bbox = TicketBoundingBox(
    x1=100, y1=200, x2=800, y2=900,
    confidence=0.95,
    source_strategy="ocr",
    page_number=page.page_number
)

# 检查面积是否满足阈值
if bbox.get_area() >= settings.ticket_detection_min_area:
    # 创建拆分结果
    width, height = bbox.get_dimensions()
    result = TicketSplitResult(
        output_path=f"{settings.ticket_output_root}/ticket_0.png",
        ticket_index=0,
        source_page=page.page_number,
        bounding_box=bbox,
        width=int(width),
        height=int(height)
    )
```

### 环境变量配置示例

```bash
# 设置检测策略为仅使用OCR
export SMART_OCR_TICKET_DETECTION_STRATEGIES=ocr

# 设置最小面积阈值
export SMART_OCR_TICKET_DETECTION_MIN_AREA=15000

# 设置输出目录
export SMART_OCR_TICKET_OUTPUT_ROOT=/data/tickets

# 设置留白像素
export SMART_OCR_TICKET_PADDING_PIXELS=20
```

## 依赖项

新增的票据检测功能需要以下依赖：

- `opencv-python-headless>=4.8.0,<5.0.0` - 用于图像处理和轮廓检测

该依赖已添加到 `requirements.txt` 中。

## 测试

运行票据配置相关测试：

```bash
# 测试配置解析
pytest tests/test_config_ticket.py -v

# 测试数据模型
pytest tests/test_pdf_ticket_models.py -v

# 运行所有测试
pytest tests/ -v
```

## 注意事项

1. **策略验证**: 环境变量中的策略名称会自动转换为小写，并验证是否为合法值
2. **目录自动创建**: 输出根目录不存在时会自动创建
3. **阈值验证**: 所有阈值参数都会进行范围验证，不符合要求会抛出异常
4. **边界框验证**: 边界框的坐标会自动验证，确保 x2 > x1 且 y2 > y1

## 后续开发

本配置为 PDF 票据拆分流程奠定了基础，后续可基于这些配置和模型实现：

1. OCR 文本检测策略实现
2. 图像轮廓检测策略实现
3. 多策略结果融合
4. 票据图像拆分与保存
5. 批量处理流程
