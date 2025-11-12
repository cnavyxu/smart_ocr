# 票据检测器使用指南

## 概述

票据检测模块提供了多种策略来检测PDF或图像中的票据区域，包括：

1. **OCR文本检测器** (`OCRTextTicketDetector`)：基于OCR文本框聚类识别票据
2. **轮廓检测器** (`ContourTicketDetector`)：基于OpenCV轮廓检测识别票据
3. **组合检测器** (`CompositeTicketDetector`)：组合多种检测策略并去重

## 安装依赖

确保安装了以下依赖：

```bash
pip install opencv-python-headless>=4.8.0
pip install scikit-learn>=1.3.0
pip install numpy>=1.24.0
```

## 快速开始

### 1. OCR文本检测器

基于OCR文本框的分布和聚类来识别票据区域。

```python
from smart_ocr.pdf_ticket.ticket_detector import (
    OCRTextTicketDetector,
    PageImage,
)
import numpy as np

# 准备OCR检测函数（如PaddleOCR）
def my_ocr_detector(image):
    # 返回文本框列表: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ...]
    # 这里使用你的OCR引擎
    pass

# 创建检测器
detector = OCRTextTicketDetector(
    ocr_detector=my_ocr_detector,
    min_text_boxes=3,        # 最少文本框数量
    min_area=10000,          # 最小面积（像素）
    eps=50.0,                # DBSCAN聚类半径
    min_samples=2            # DBSCAN最小样本数
)

# 准备图像
image = np.array(...)  # BGR格式的图像
page = PageImage(image=image, page_number=1)

# 执行检测
tickets = detector.detect(page)

# 处理结果
for ticket in tickets:
    print(f"位置: ({ticket.x}, {ticket.y})")
    print(f"尺寸: {ticket.width} x {ticket.height}")
    print(f"置信度: {ticket.confidence}")
```

### 2. 轮廓检测器

使用OpenCV的图像处理技术检测票据区域。

```python
from smart_ocr.pdf_ticket.ticket_detector import (
    ContourTicketDetector,
    PageImage,
)

# 创建检测器
detector = ContourTicketDetector(
    min_area=5000,              # 最小轮廓面积
    max_area=0.9,               # 最大面积比例
    min_aspect_ratio=0.3,       # 最小长宽比
    max_aspect_ratio=3.0,       # 最大长宽比
    canny_threshold1=50,        # Canny低阈值
    canny_threshold2=150,       # Canny高阈值
    blur_kernel_size=5,         # 高斯模糊核大小
    morph_kernel_size=5         # 形态学操作核大小
)

# 执行检测
tickets = detector.detect(page)
```

### 3. 组合检测器

组合多个检测器，自动去除重复区域。

```python
from smart_ocr.pdf_ticket.ticket_detector import (
    OCRTextTicketDetector,
    ContourTicketDetector,
    CompositeTicketDetector,
)

# 创建多个检测器
ocr_detector = OCRTextTicketDetector(
    ocr_detector=my_ocr_detector,
    min_text_boxes=3
)

contour_detector = ContourTicketDetector(
    min_area=5000
)

# 创建组合检测器
composite = CompositeTicketDetector(
    detectors=[ocr_detector, contour_detector],
    iou_threshold=0.5  # IOU阈值，超过此值视为重复
)

# 执行检测（自动去重）
tickets = composite.detect(page)
```

## 配置说明

### 环境变量配置

所有参数都可以通过环境变量配置（前缀：`SMART_OCR_`）：

```bash
# OCR检测器参数
export SMART_OCR_TICKET_MIN_TEXT_BOXES=3
export SMART_OCR_TICKET_MIN_AREA=10000
export SMART_OCR_TICKET_CLUSTER_EPS=50.0
export SMART_OCR_TICKET_CLUSTER_MIN_SAMPLES=2

# 轮廓检测器参数
export SMART_OCR_CONTOUR_MIN_AREA=5000
export SMART_OCR_CONTOUR_MAX_AREA_RATIO=0.9
export SMART_OCR_CONTOUR_MIN_ASPECT_RATIO=0.3
export SMART_OCR_CONTOUR_MAX_ASPECT_RATIO=3.0
export SMART_OCR_CANNY_THRESHOLD1=50
export SMART_OCR_CANNY_THRESHOLD2=150
export SMART_OCR_BLUR_KERNEL_SIZE=5
export SMART_OCR_MORPH_KERNEL_SIZE=5
```

### 参数说明

#### OCR文本检测器参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_text_boxes` | int | 3 | 票据区域最少包含的文本框数量 |
| `min_area` | int | 10000 | 票据最小面积（像素） |
| `eps` | float | 50.0 | DBSCAN聚类的邻域半径 |
| `min_samples` | int | 2 | DBSCAN聚类的最小样本数 |

#### 轮廓检测器参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_area` | int | 5000 | 轮廓最小面积 |
| `max_area` | float | 0.9 | 轮廓最大面积占图像面积的比例 |
| `min_aspect_ratio` | float | 0.3 | 轮廓最小长宽比 |
| `max_aspect_ratio` | float | 3.0 | 轮廓最大长宽比 |
| `canny_threshold1` | int | 50 | Canny边缘检测低阈值 |
| `canny_threshold2` | int | 150 | Canny边缘检测高阈值 |
| `blur_kernel_size` | int | 5 | 高斯模糊核大小 |
| `morph_kernel_size` | int | 5 | 形态学操作核大小 |

## 数据结构

### PageImage

表示单个页面图像：

```python
@dataclass
class PageImage:
    image: np.ndarray      # BGR格式的图像数据
    page_number: int = 1   # 页码（从1开始）
    width: int             # 自动计算的宽度
    height: int            # 自动计算的高度
```

### TicketBoundingBox

表示票据边界框：

```python
@dataclass
class TicketBoundingBox:
    x: int                      # 左上角x坐标
    y: int                      # 左上角y坐标
    width: int                  # 宽度
    height: int                 # 高度
    confidence: float = 1.0     # 置信度 (0-1)
    source: str = "unknown"     # 来源标签
    page_number: int = 1        # 页码

    def area(self) -> int:
        """计算面积"""
        
    def iou(self, other) -> float:
        """计算与另一个框的IOU"""
        
    def to_dict(self) -> dict:
        """转换为字典"""
```

## 异常处理

所有检测器都会抛出 `TicketDetectionError` 异常：

```python
from smart_ocr.pdf_ticket.ticket_detector import TicketDetectionError

try:
    tickets = detector.detect(page)
except TicketDetectionError as e:
    print(f"检测失败: {e}")
    if e.cause:
        print(f"原因: {e.cause}")
```

## 日志记录

检测器会输出详细的日志信息，便于调试：

```python
import logging

# 配置日志级别
logging.basicConfig(level=logging.INFO)

# 日志输出示例：
# INFO - 页面 1: OCR检测到 2 个票据区域 (文本框总数: 15)
# INFO - 页面 1: 轮廓检测到 3 个票据区域 (总轮廓数: 5)
# INFO - 页面 1: 组合检测器检测到 2 个票据区域 (合并前: 5)
```

## 最佳实践

### 1. 选择合适的检测策略

- **清晰的扫描件**：使用轮廓检测器，速度快且准确
- **复杂背景/拍照图片**：使用OCR文本检测器，更可靠
- **生产环境**：使用组合检测器，综合两种策略的优势

### 2. 调整参数

根据实际票据特征调整参数：

```python
# 小票据：降低最小面积阈值
detector = ContourTicketDetector(min_area=2000)

# 密集文本：增大聚类半径
detector = OCRTextTicketDetector(eps=100.0)

# 严格过滤：提高置信度要求
tickets = [t for t in detector.detect(page) if t.confidence > 0.8]
```

### 3. 性能优化

```python
# 缓存OCR检测结果
ocr_cache = {}

def cached_ocr_detector(image):
    key = hash(image.tobytes())
    if key not in ocr_cache:
        ocr_cache[key] = actual_ocr_function(image)
    return ocr_cache[key]

detector = OCRTextTicketDetector(ocr_detector=cached_ocr_detector)
```

### 4. 结果后处理

```python
# 按面积排序
tickets = sorted(detector.detect(page), key=lambda t: t.area(), reverse=True)

# 过滤重叠票据
def remove_nested_tickets(tickets):
    """移除完全包含在其他票据内的小票据"""
    result = []
    for i, t1 in enumerate(tickets):
        nested = False
        for j, t2 in enumerate(tickets):
            if i != j and t1.iou(t2) > 0.8 and t1.area() < t2.area():
                nested = True
                break
        if not nested:
            result.append(t1)
    return result

tickets = remove_nested_tickets(tickets)
```

## 示例

完整的使用示例请参考：`examples_ticket_detector.py`

运行示例：

```bash
python examples_ticket_detector.py
```

## 常见问题

### 1. 检测不到票据

- 检查图像质量和分辨率
- 降低 `min_area` 阈值
- 对于OCR检测器，降低 `min_text_boxes`
- 对于轮廓检测器，调整Canny阈值

### 2. 检测到过多误报

- 提高 `min_area` 阈值
- 调整长宽比过滤范围
- 提高置信度阈值
- 使用组合检测器并调整IOU阈值

### 3. 边界不准确

- 使用OCR文本检测器获取文本精确边界
- 调整DBSCAN的 `eps` 参数
- 尝试组合多个检测器

### 4. 性能问题

- 缓存OCR检测结果
- 降低图像分辨率（在保证质量的前提下）
- 使用轮廓检测器（比OCR快）
- 并行处理多页

## 技术细节

### OCR文本聚类算法

1. 提取所有文本框的中心点
2. 使用DBSCAN算法聚类
3. 为每个聚类计算最小包围矩形
4. 根据文本密度计算置信度
5. 过滤面积过小的区域

### 轮廓检测流程

1. 灰度化
2. 高斯模糊去噪
3. Canny边缘检测
4. 形态学闭操作连接边缘
5. 查找外部轮廓
6. 过滤面积和长宽比
7. 计算矩形相似度作为置信度

### 去重策略

组合检测器使用IOU（交并比）判断重复：

- IOU > threshold：视为重复，保留置信度高的
- IOU ≤ threshold：视为不同票据，都保留

## 扩展开发

### 自定义检测器

```python
from smart_ocr.pdf_ticket.ticket_detector import BaseTicketDetector

class MyCustomDetector(BaseTicketDetector):
    def detect(self, page: PageImage) -> List[TicketBoundingBox]:
        # 实现你的检测逻辑
        tickets = []
        # ...
        return tickets

# 使用自定义检测器
detector = MyCustomDetector()
tickets = detector.detect(page)
```

### 集成到现有系统

```python
# 与PaddleOCR集成
from paddleocr import PaddleOCR

paddle_ocr = PaddleOCR(use_angle_cls=True, lang='ch')

def paddle_text_detector(image):
    result = paddle_ocr.ocr(image, det=True, rec=False)
    return [line[0] for line in result[0]] if result[0] else []

detector = OCRTextTicketDetector(ocr_detector=paddle_text_detector)
```

## 参考资料

- [OpenCV文档](https://docs.opencv.org/)
- [scikit-learn DBSCAN](https://scikit-learn.org/stable/modules/clustering.html#dbscan)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
