"""票据检测模块。

本模块实现了多种票据检测策略，包括基于OCR文本聚类、基于OpenCV轮廓检测
以及组合多种检测器的复合策略。所有检测器实现统一的接口，便于扩展和组合。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Protocol, Tuple

import cv2
import numpy as np
from sklearn.cluster import DBSCAN

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class TicketDetectionError(Exception):
    """票据检测过程中发生的异常。
    
    用于统一包装底层异常，提供更清晰的错误上下文。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """初始化票据检测异常。
        
        Args:
            message: 错误描述信息
            cause: 导致此异常的底层异常
        """
        super().__init__(message)
        self.cause = cause
        if cause:
            self.__cause__ = cause


@dataclass
class PageImage:
    """表示单个页面图像。
    
    Attributes:
        image: NumPy数组表示的图像数据，BGR格式
        page_number: 页码，从1开始
        width: 图像宽度（像素）
        height: 图像高度（像素）
    """

    image: np.ndarray
    page_number: int = 1
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        """初始化后自动计算图像尺寸。"""
        if self.image is None or len(self.image.shape) < 2:
            raise ValueError("图像数据无效")
        self.height, self.width = self.image.shape[:2]


@dataclass
class TicketBoundingBox:
    """票据边界框。
    
    Attributes:
        x: 左上角x坐标
        y: 左上角y坐标
        width: 边界框宽度
        height: 边界框高度
        confidence: 置信度分数 (0-1)
        source: 检测来源标签（如 "ocr", "contour", "composite"）
        page_number: 所属页码，从1开始
    """

    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    source: str = "unknown"
    page_number: int = 1

    def area(self) -> int:
        """计算边界框面积。
        
        Returns:
            边界框的像素面积
        """
        return self.width * self.height

    def iou(self, other: TicketBoundingBox) -> float:
        """计算与另一个边界框的交并比(IOU)。
        
        Args:
            other: 另一个边界框
            
        Returns:
            交并比值，范围 [0, 1]
        """
        # 计算交集区域
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = self.area() + other.area() - intersection

        return intersection / union if union > 0 else 0.0

    def to_dict(self) -> dict:
        """转换为字典表示。
        
        Returns:
            包含所有字段的字典
        """
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "source": self.source,
            "page_number": self.page_number,
        }


class BaseTicketDetector(ABC):
    """票据检测器抽象基类。
    
    定义所有票据检测器必须实现的接口。
    """

    @abstractmethod
    def detect(self, page: PageImage) -> List[TicketBoundingBox]:
        """检测页面中的票据区域。
        
        Args:
            page: 待检测的页面图像
            
        Returns:
            检测到的票据边界框列表
            
        Raises:
            TicketDetectionError: 检测过程中发生错误
        """
        pass


class OCRTextTicketDetector(BaseTicketDetector):
    """基于OCR文本检测的票据检测器。
    
    通过分析OCR文本框的分布和聚类来识别票据区域。
    使用DBSCAN算法对文本框进行聚类，每个聚类对应一个可能的票据。
    """

    def __init__(
        self,
        ocr_detector: Callable[[np.ndarray], List[List[List[float]]]],
        settings: Optional[Settings] = None,
        min_text_boxes: Optional[int] = None,
        min_area: Optional[int] = None,
        eps: Optional[float] = None,
        min_samples: Optional[int] = None,
    ):
        """初始化OCR文本票据检测器。
        
        Args:
            ocr_detector: OCR检测函数，接受图像返回文本框列表
                         每个文本框格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            settings: 配置对象，如果为None则使用全局配置
            min_text_boxes: 最小文本框数量阈值，低于此值的聚类将被过滤
            min_area: 最小票据面积阈值（像素）
            eps: DBSCAN聚类的邻域半径
            min_samples: DBSCAN聚类的最小样本数
        """
        self.ocr_detector = ocr_detector
        self.settings = settings or get_settings()
        self.min_text_boxes = min_text_boxes or getattr(
            self.settings, "ticket_min_text_boxes", 3
        )
        self.min_area = min_area or getattr(
            self.settings, "ticket_min_area", 10000
        )
        self.eps = eps or getattr(self.settings, "ticket_cluster_eps", 50.0)
        self.min_samples = min_samples or getattr(
            self.settings, "ticket_cluster_min_samples", 2
        )

    def detect(self, page: PageImage) -> List[TicketBoundingBox]:
        """使用OCR文本检测票据区域。
        
        Args:
            page: 待检测的页面图像
            
        Returns:
            检测到的票据边界框列表
            
        Raises:
            TicketDetectionError: OCR检测或聚类过程中发生错误
        """
        try:
            # 调用OCR检测器获取文本框
            text_boxes = self.ocr_detector(page.image)
            
            if not text_boxes:
                logger.info(f"页面 {page.page_number}: 未检测到文本框")
                return []

            # 提取文本框中心点用于聚类
            centers = []
            boxes = []
            for box in text_boxes:
                if not box or len(box) != 4:
                    continue
                # 计算文本框中心点
                points = np.array(box, dtype=np.float32)
                center = points.mean(axis=0)
                centers.append(center)
                boxes.append(box)

            if len(centers) < self.min_text_boxes:
                logger.info(
                    f"页面 {page.page_number}: 文本框数量({len(centers)})不足，"
                    f"需要至少 {self.min_text_boxes} 个"
                )
                return []

            # 使用DBSCAN进行聚类
            centers_array = np.array(centers)
            clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples)
            labels = clustering.fit_predict(centers_array)

            # 为每个聚类生成边界框
            tickets = []
            unique_labels = set(labels)
            unique_labels.discard(-1)  # 移除噪声点标签

            for label in unique_labels:
                # 获取属于当前聚类的所有文本框
                cluster_indices = np.where(labels == label)[0]
                
                if len(cluster_indices) < self.min_text_boxes:
                    continue

                # 计算包围所有文本框的最小矩形
                all_points = []
                for idx in cluster_indices:
                    box = boxes[idx]
                    all_points.extend(box)

                all_points = np.array(all_points, dtype=np.float32)
                x_min = int(all_points[:, 0].min())
                y_min = int(all_points[:, 1].min())
                x_max = int(all_points[:, 0].max())
                y_max = int(all_points[:, 1].max())

                width = x_max - x_min
                height = y_max - y_min
                area = width * height

                # 过滤面积过小的区域
                if area < self.min_area:
                    continue

                # 计算置信度（基于文本框密度）
                density = len(cluster_indices) / (area / 1000.0)  # 每千像素的文本框数
                confidence = min(density / 10.0, 1.0)  # 归一化到0-1

                ticket = TicketBoundingBox(
                    x=x_min,
                    y=y_min,
                    width=width,
                    height=height,
                    confidence=confidence,
                    source="ocr",
                    page_number=page.page_number,
                )
                tickets.append(ticket)

            logger.info(
                f"页面 {page.page_number}: OCR检测到 {len(tickets)} 个票据区域 "
                f"(文本框总数: {len(text_boxes)})"
            )
            return tickets

        except Exception as e:
            raise TicketDetectionError(
                f"OCR文本检测失败 (页面 {page.page_number}): {str(e)}", cause=e
            )


class ContourTicketDetector(BaseTicketDetector):
    """基于OpenCV轮廓检测的票据检测器。
    
    使用图像处理技术检测票据区域：
    1. 灰度化
    2. 高斯模糊
    3. Canny边缘检测
    4. 形态学操作（膨胀/闭操作）
    5. 轮廓检测
    6. 过滤和筛选
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        min_area: Optional[int] = None,
        max_area: Optional[int] = None,
        min_aspect_ratio: Optional[float] = None,
        max_aspect_ratio: Optional[float] = None,
        canny_threshold1: Optional[int] = None,
        canny_threshold2: Optional[int] = None,
        blur_kernel_size: Optional[int] = None,
        morph_kernel_size: Optional[int] = None,
    ):
        """初始化轮廓票据检测器。
        
        Args:
            settings: 配置对象，如果为None则使用全局配置
            min_area: 最小轮廓面积阈值
            max_area: 最大轮廓面积阈值（占图像面积的比例，0-1）
            min_aspect_ratio: 最小长宽比
            max_aspect_ratio: 最大长宽比
            canny_threshold1: Canny边缘检测的低阈值
            canny_threshold2: Canny边缘检测的高阈值
            blur_kernel_size: 高斯模糊核大小
            morph_kernel_size: 形态学操作核大小
        """
        self.settings = settings or get_settings()
        self.min_area = min_area or getattr(
            self.settings, "contour_min_area", 5000
        )
        self.max_area = max_area or getattr(
            self.settings, "contour_max_area_ratio", 0.9
        )
        self.min_aspect_ratio = min_aspect_ratio or getattr(
            self.settings, "contour_min_aspect_ratio", 0.3
        )
        self.max_aspect_ratio = max_aspect_ratio or getattr(
            self.settings, "contour_max_aspect_ratio", 3.0
        )
        self.canny_threshold1 = canny_threshold1 or getattr(
            self.settings, "canny_threshold1", 50
        )
        self.canny_threshold2 = canny_threshold2 or getattr(
            self.settings, "canny_threshold2", 150
        )
        self.blur_kernel_size = blur_kernel_size or getattr(
            self.settings, "blur_kernel_size", 5
        )
        self.morph_kernel_size = morph_kernel_size or getattr(
            self.settings, "morph_kernel_size", 5
        )

    def detect(self, page: PageImage) -> List[TicketBoundingBox]:
        """使用轮廓检测票据区域。
        
        Args:
            page: 待检测的页面图像
            
        Returns:
            检测到的票据边界框列表
            
        Raises:
            TicketDetectionError: 图像处理过程中发生错误
        """
        try:
            image = page.image
            image_area = page.width * page.height
            max_area_pixels = int(image_area * self.max_area)

            # 1. 灰度化
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 2. 高斯模糊
            blurred = cv2.GaussianBlur(
                gray, (self.blur_kernel_size, self.blur_kernel_size), 0
            )

            # 3. Canny边缘检测
            edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)

            # 4. 形态学闭操作，连接断开的边缘
            kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (self.morph_kernel_size, self.morph_kernel_size),
            )
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

            # 5. 检测轮廓
            contours, _ = cv2.findContours(
                closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            tickets = []
            for contour in contours:
                # 计算轮廓边界框
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                # 过滤面积
                if area < self.min_area or area > max_area_pixels:
                    continue

                # 过滤长宽比
                aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
                if (
                    aspect_ratio < self.min_aspect_ratio
                    or aspect_ratio > self.max_aspect_ratio
                ):
                    continue

                # 计算轮廓近似度（矩形相似度）
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
                
                # 计算置信度（基于顶点数，4个顶点的矩形置信度最高）
                vertex_score = 1.0 - min(abs(len(approx) - 4) / 10.0, 0.5)
                
                # 计算轮廓填充率
                contour_area = cv2.contourArea(contour)
                fill_ratio = contour_area / area if area > 0 else 0
                
                confidence = (vertex_score + fill_ratio) / 2.0

                ticket = TicketBoundingBox(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=confidence,
                    source="contour",
                    page_number=page.page_number,
                )
                tickets.append(ticket)

            logger.info(
                f"页面 {page.page_number}: 轮廓检测到 {len(tickets)} 个票据区域 "
                f"(总轮廓数: {len(contours)})"
            )
            return tickets

        except Exception as e:
            raise TicketDetectionError(
                f"轮廓检测失败 (页面 {page.page_number}): {str(e)}", cause=e
            )


class CompositeTicketDetector(BaseTicketDetector):
    """组合多个检测器的复合检测器。
    
    按照指定顺序执行多个检测器，合并结果并去除重复的边界框。
    使用IOU阈值判断边界框是否重复，保留置信度最高的边界框。
    """

    def __init__(
        self,
        detectors: List[BaseTicketDetector],
        iou_threshold: float = 0.5,
    ):
        """初始化复合检测器。
        
        Args:
            detectors: 检测器列表，按执行顺序排列
            iou_threshold: IOU阈值，高于此值的边界框被视为重复
        """
        if not detectors:
            raise ValueError("至少需要提供一个检测器")
        self.detectors = detectors
        self.iou_threshold = iou_threshold

    def detect(self, page: PageImage) -> List[TicketBoundingBox]:
        """使用多个检测器检测票据区域并合并结果。
        
        Args:
            page: 待检测的页面图像
            
        Returns:
            去重后的票据边界框列表
            
        Raises:
            TicketDetectionError: 任一检测器执行失败
        """
        all_tickets = []
        
        # 执行所有检测器
        for detector in self.detectors:
            try:
                tickets = detector.detect(page)
                all_tickets.extend(tickets)
            except TicketDetectionError as e:
                logger.warning(
                    f"检测器 {detector.__class__.__name__} 执行失败: {str(e)}"
                )
                # 继续执行其他检测器

        if not all_tickets:
            logger.info(f"页面 {page.page_number}: 所有检测器均未检测到票据")
            return []

        # 去重：使用IOU阈值合并重复的边界框
        merged_tickets = self._merge_overlapping_boxes(all_tickets)

        logger.info(
            f"页面 {page.page_number}: 组合检测器检测到 {len(merged_tickets)} 个票据区域 "
            f"(合并前: {len(all_tickets)})"
        )
        return merged_tickets

    def _merge_overlapping_boxes(
        self, tickets: List[TicketBoundingBox]
    ) -> List[TicketBoundingBox]:
        """合并重叠的边界框。
        
        Args:
            tickets: 待合并的票据边界框列表
            
        Returns:
            去重后的边界框列表，每组重叠框仅保留置信度最高的一个
        """
        if not tickets:
            return []

        # 按置信度降序排序
        sorted_tickets = sorted(tickets, key=lambda t: t.confidence, reverse=True)
        
        merged = []
        used = set()

        for i, ticket in enumerate(sorted_tickets):
            if i in used:
                continue

            # 检查是否与已选中的框重叠
            is_duplicate = False
            for j in used:
                if ticket.iou(sorted_tickets[j]) > self.iou_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged.append(ticket)
                used.add(i)

        return merged
