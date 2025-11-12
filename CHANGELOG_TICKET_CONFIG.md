# 变更日志 - 票据配置功能

## [新增] PDF票据检测与拆分配置 (2024-11-12)

### 新增功能

#### 1. PDF票据模块 (`smart_ocr.pdf_ticket`)

新增了专门的票据处理模块，包含三个核心数据模型：

- **PageImage**: PDF页面图像及元数据模型
- **TicketBoundingBox**: 票据边界框检测结果模型
- **TicketSplitResult**: 票据拆分结果记录模型

#### 2. 票据配置项

在全局配置中新增 7 个票据相关配置项：

| 配置项 | 环境变量 | 默认值 |
|--------|----------|--------|
| 检测策略 | `SMART_OCR_TICKET_DETECTION_STRATEGIES` | `['ocr', 'contour']` |
| 允许OCR检测 | `SMART_OCR_TICKET_ALLOW_OCR_DETECTION` | `True` |
| 允许轮廓检测 | `SMART_OCR_TICKET_ALLOW_CONTOUR_DETECTION` | `True` |
| 最小面积阈值 | `SMART_OCR_TICKET_DETECTION_MIN_AREA` | `10000` |
| 最小文本字符数 | `SMART_OCR_TICKET_DETECTION_MIN_TEXT` | `10` |
| 输出根目录 | `SMART_OCR_TICKET_OUTPUT_ROOT` | `./outputs/tickets` |
| 留白像素数 | `SMART_OCR_TICKET_PADDING_PIXELS` | `10` |

#### 3. 完整的配置验证

实现了完善的配置验证机制：
- 策略名称合法性验证
- 输出目录自动创建
- 参数范围验证
- 环境变量灵活解析

#### 4. 新增依赖

添加了 `opencv-python-headless>=4.8.0,<5.0.0` 依赖，用于图像处理和轮廓检测。

### 测试覆盖

新增 63 个单元测试，覆盖：
- 配置项解析和验证 (32 个测试)
- 数据模型创建和验证 (31 个测试)
- 所有测试通过率 100%

### 文档

新增文档：
- `docs/TICKET_CONFIG.md` - 完整的配置和使用文档
- `TICKET_IMPLEMENTATION_SUMMARY.md` - 实现总结文档
- `test_ticket_config_demo.py` - 功能演示脚本

### 文件变更

**新增文件:**
- `src/smart_ocr/pdf_ticket/__init__.py`
- `src/smart_ocr/pdf_ticket/models.py`
- `tests/__init__.py`
- `tests/test_config_ticket.py`
- `tests/test_pdf_ticket_models.py`

**修改文件:**
- `src/smart_ocr/config.py` - 添加票据配置项
- `src/smart_ocr/__init__.py` - 导出 pdf_ticket 模块
- `requirements.txt` - 添加 opencv-python-headless
- `.gitignore` - 添加 outputs/ 目录

### 使用示例

```python
from smart_ocr.config import get_settings
from smart_ocr.pdf_ticket import PageImage, TicketBoundingBox, TicketSplitResult

# 获取配置
settings = get_settings()

# 创建页面模型
page = PageImage(page_number=1, width=1920, height=1080, dpi=220)

# 创建边界框
bbox = TicketBoundingBox(
    x1=100, y1=200, x2=800, y2=900,
    confidence=0.95,
    source_strategy="ocr",
    page_number=1
)

# 创建拆分结果
result = TicketSplitResult(
    output_path="./outputs/tickets/ticket_0.png",
    ticket_index=0,
    source_page=1,
    bounding_box=bbox,
    width=700,
    height=700
)
```

### 向后兼容性

本次更新完全向后兼容，不影响现有功能。所有新增配置项都有合理的默认值。

### 下一步

基于本次实现，可继续开发：
1. OCR文本检测策略
2. 图像轮廓检测策略
3. 多策略融合算法
4. 票据图像拆分功能
5. 批量处理流程
