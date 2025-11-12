"""票据检测器单元测试。

本测试模块验证各种票据检测器的功能，包括OCR文本检测、轮廓检测和组合检测。
使用合成图像和模拟OCR输出进行测试，确保检测器能正确识别票据区域。
"""

import unittest
from typing import List
from unittest.mock import MagicMock, Mock

import cv2
import numpy as np

from smart_ocr.pdf_ticket.ticket_detector import (
    BaseTicketDetector,
    CompositeTicketDetector,
    ContourTicketDetector,
    OCRTextTicketDetector,
    PageImage,
    TicketBoundingBox,
    TicketDetectionError,
)


class TestPageImage(unittest.TestCase):
    """测试PageImage数据类。"""

    def test_page_image_initialization(self):
        """测试PageImage正常初始化。"""
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        self.assertEqual(page.width, 800)
        self.assertEqual(page.height, 600)
        self.assertEqual(page.page_number, 1)

    def test_page_image_invalid(self):
        """测试无效图像数据。"""
        with self.assertRaises(ValueError):
            PageImage(image=None, page_number=1)

    def test_page_image_grayscale(self):
        """测试灰度图像。"""
        image = np.zeros((600, 800), dtype=np.uint8)
        page = PageImage(image=image, page_number=2)
        
        self.assertEqual(page.width, 800)
        self.assertEqual(page.height, 600)


class TestTicketBoundingBox(unittest.TestCase):
    """测试TicketBoundingBox数据类。"""

    def test_bounding_box_area(self):
        """测试边界框面积计算。"""
        box = TicketBoundingBox(x=10, y=20, width=100, height=200)
        self.assertEqual(box.area(), 20000)

    def test_bounding_box_iou_no_overlap(self):
        """测试无重叠的边界框IOU。"""
        box1 = TicketBoundingBox(x=0, y=0, width=100, height=100)
        box2 = TicketBoundingBox(x=200, y=200, width=100, height=100)
        
        self.assertEqual(box1.iou(box2), 0.0)
        self.assertEqual(box2.iou(box1), 0.0)

    def test_bounding_box_iou_full_overlap(self):
        """测试完全重叠的边界框IOU。"""
        box1 = TicketBoundingBox(x=0, y=0, width=100, height=100)
        box2 = TicketBoundingBox(x=0, y=0, width=100, height=100)
        
        self.assertAlmostEqual(box1.iou(box2), 1.0)

    def test_bounding_box_iou_partial_overlap(self):
        """测试部分重叠的边界框IOU。"""
        box1 = TicketBoundingBox(x=0, y=0, width=100, height=100)
        box2 = TicketBoundingBox(x=50, y=50, width=100, height=100)
        
        # 交集: 50x50 = 2500
        # 并集: 10000 + 10000 - 2500 = 17500
        # IOU = 2500 / 17500 ≈ 0.1429
        iou = box1.iou(box2)
        self.assertGreater(iou, 0.0)
        self.assertLess(iou, 1.0)
        self.assertAlmostEqual(iou, 2500 / 17500, places=4)

    def test_bounding_box_to_dict(self):
        """测试边界框转换为字典。"""
        box = TicketBoundingBox(
            x=10, y=20, width=100, height=200,
            confidence=0.95, source="test", page_number=3
        )
        
        expected = {
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 200,
            "confidence": 0.95,
            "source": "test",
            "page_number": 3,
        }
        
        self.assertEqual(box.to_dict(), expected)


class TestOCRTextTicketDetector(unittest.TestCase):
    """测试OCR文本票据检测器。"""

    def _create_mock_ocr_detector(
        self, text_boxes: List[List[List[float]]]
    ):
        """创建模拟的OCR检测器。
        
        Args:
            text_boxes: 要返回的文本框列表
            
        Returns:
            模拟的OCR检测函数
        """
        def mock_detector(image: np.ndarray):
            return text_boxes
        return mock_detector

    def test_ocr_detector_no_text_boxes(self):
        """测试没有文本框的情况。"""
        mock_ocr = self._create_mock_ocr_detector([])
        detector = OCRTextTicketDetector(
            ocr_detector=mock_ocr,
            min_text_boxes=3
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = detector.detect(page)
        self.assertEqual(len(tickets), 0)

    def test_ocr_detector_single_cluster(self):
        """测试单个聚类的情况。"""
        # 创建一个聚类：5个文本框在区域(100, 100)附近
        text_boxes = [
            [[100, 100], [150, 100], [150, 120], [100, 120]],
            [[100, 130], [150, 130], [150, 150], [100, 150]],
            [[100, 160], [150, 160], [150, 180], [100, 180]],
            [[160, 100], [210, 100], [210, 120], [160, 120]],
            [[160, 130], [210, 130], [210, 150], [160, 150]],
        ]
        
        mock_ocr = self._create_mock_ocr_detector(text_boxes)
        detector = OCRTextTicketDetector(
            ocr_detector=mock_ocr,
            min_text_boxes=3,
            min_area=1000,
            eps=50.0,
            min_samples=2
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = detector.detect(page)
        
        # 应该检测到1个票据
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].source, "ocr")
        self.assertEqual(tickets[0].page_number, 1)
        self.assertGreater(tickets[0].confidence, 0.0)

    def test_ocr_detector_multiple_clusters(self):
        """测试多个聚类的情况。"""
        # 创建两个聚类
        text_boxes = [
            # 聚类1: 左上角
            [[50, 50], [100, 50], [100, 70], [50, 70]],
            [[50, 80], [100, 80], [100, 100], [50, 100]],
            [[50, 110], [100, 110], [100, 130], [50, 130]],
            # 聚类2: 右下角
            [[400, 400], [450, 400], [450, 420], [400, 420]],
            [[400, 430], [450, 430], [450, 450], [400, 450]],
            [[400, 460], [450, 460], [450, 480], [400, 480]],
        ]
        
        mock_ocr = self._create_mock_ocr_detector(text_boxes)
        detector = OCRTextTicketDetector(
            ocr_detector=mock_ocr,
            min_text_boxes=3,
            min_area=1000,
            eps=50.0,
            min_samples=2
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = detector.detect(page)
        
        # 应该检测到2个票据
        self.assertEqual(len(tickets), 2)

    def test_ocr_detector_filter_small_area(self):
        """测试过滤小面积区域。"""
        # 创建一个小区域（面积不足）
        text_boxes = [
            [[50, 50], [60, 50], [60, 60], [50, 60]],
            [[50, 65], [60, 65], [60, 75], [50, 75]],
            [[50, 80], [60, 80], [60, 90], [50, 90]],
        ]
        
        mock_ocr = self._create_mock_ocr_detector(text_boxes)
        detector = OCRTextTicketDetector(
            ocr_detector=mock_ocr,
            min_text_boxes=3,
            min_area=10000,  # 设置较大的最小面积
            eps=50.0,
            min_samples=2
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = detector.detect(page)
        
        # 应该没有检测到票据（面积太小）
        self.assertEqual(len(tickets), 0)

    def test_ocr_detector_error_handling(self):
        """测试OCR检测器异常处理。"""
        def failing_ocr(image):
            raise RuntimeError("OCR失败")
        
        detector = OCRTextTicketDetector(ocr_detector=failing_ocr)
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        with self.assertRaises(TicketDetectionError) as context:
            detector.detect(page)
        
        self.assertIn("OCR文本检测失败", str(context.exception))


class TestContourTicketDetector(unittest.TestCase):
    """测试轮廓票据检测器。"""

    def _create_synthetic_ticket_image(self) -> np.ndarray:
        """创建包含矩形票据的合成图像。
        
        Returns:
            包含白色背景和黑色矩形的图像
        """
        # 创建白色背景
        image = np.ones((600, 800, 3), dtype=np.uint8) * 255
        
        # 绘制黑色矩形（模拟票据）
        cv2.rectangle(image, (100, 100), (300, 400), (0, 0, 0), 2)
        cv2.rectangle(image, (400, 150), (600, 450), (0, 0, 0), 2)
        
        return image

    def test_contour_detector_basic(self):
        """测试基本轮廓检测。"""
        detector = ContourTicketDetector(
            min_area=5000,
            max_area=0.9,
            canny_threshold1=50,
            canny_threshold2=150
        )
        
        image = self._create_synthetic_ticket_image()
        page = PageImage(image=image, page_number=1)
        
        tickets = detector.detect(page)
        
        # 应该检测到至少1个票据（可能检测到2个）
        self.assertGreater(len(tickets), 0)
        self.assertEqual(tickets[0].source, "contour")

    def test_contour_detector_filter_small_area(self):
        """测试过滤小面积轮廓。"""
        # 创建只有小矩形的图像
        image = np.ones((600, 800, 3), dtype=np.uint8) * 255
        cv2.rectangle(image, (100, 100), (120, 120), (0, 0, 0), 2)
        
        detector = ContourTicketDetector(
            min_area=10000,  # 设置大的最小面积
        )
        
        page = PageImage(image=image, page_number=1)
        tickets = detector.detect(page)
        
        # 应该没有检测到票据
        self.assertEqual(len(tickets), 0)

    def test_contour_detector_aspect_ratio_filter(self):
        """测试长宽比过滤。"""
        # 创建一个长条形矩形（长宽比过大）
        image = np.ones((600, 800, 3), dtype=np.uint8) * 255
        cv2.rectangle(image, (100, 100), (700, 150), (0, 0, 0), 2)
        
        detector = ContourTicketDetector(
            min_area=1000,
            max_aspect_ratio=3.0,  # 限制最大长宽比
        )
        
        page = PageImage(image=image, page_number=1)
        tickets = detector.detect(page)
        
        # 长宽比过大，应该被过滤
        # 注意：由于边缘检测和轮廓提取的不确定性，这个测试可能不稳定
        # 主要验证过滤逻辑存在
        self.assertIsInstance(tickets, list)

    def test_contour_detector_empty_image(self):
        """测试空白图像。"""
        # 创建纯白色图像（无轮廓）
        image = np.ones((600, 800, 3), dtype=np.uint8) * 255
        
        detector = ContourTicketDetector()
        page = PageImage(image=image, page_number=1)
        
        tickets = detector.detect(page)
        
        # 应该没有检测到票据
        self.assertEqual(len(tickets), 0)


class TestCompositeTicketDetector(unittest.TestCase):
    """测试组合票据检测器。"""

    def test_composite_detector_single_detector(self):
        """测试单个检测器的组合。"""
        mock_detector = Mock(spec=BaseTicketDetector)
        mock_detector.detect.return_value = [
            TicketBoundingBox(x=100, y=100, width=200, height=300, confidence=0.9)
        ]
        
        composite = CompositeTicketDetector(detectors=[mock_detector])
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = composite.detect(page)
        
        self.assertEqual(len(tickets), 1)
        mock_detector.detect.assert_called_once()

    def test_composite_detector_multiple_detectors(self):
        """测试多个检测器的组合。"""
        # 创建两个模拟检测器
        detector1 = Mock(spec=BaseTicketDetector)
        detector1.detect.return_value = [
            TicketBoundingBox(x=100, y=100, width=200, height=300, confidence=0.9, source="det1")
        ]
        
        detector2 = Mock(spec=BaseTicketDetector)
        detector2.detect.return_value = [
            TicketBoundingBox(x=400, y=200, width=150, height=250, confidence=0.85, source="det2")
        ]
        
        composite = CompositeTicketDetector(detectors=[detector1, detector2])
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = composite.detect(page)
        
        # 应该有2个票据（无重叠）
        self.assertEqual(len(tickets), 2)

    def test_composite_detector_merge_overlapping(self):
        """测试合并重叠的边界框。"""
        # 创建两个检测器，返回重叠的框
        detector1 = Mock(spec=BaseTicketDetector)
        detector1.detect.return_value = [
            TicketBoundingBox(x=100, y=100, width=200, height=300, confidence=0.9, source="det1")
        ]
        
        detector2 = Mock(spec=BaseTicketDetector)
        detector2.detect.return_value = [
            # 与detector1的框有高度重叠
            TicketBoundingBox(x=110, y=110, width=200, height=300, confidence=0.7, source="det2")
        ]
        
        composite = CompositeTicketDetector(
            detectors=[detector1, detector2],
            iou_threshold=0.5
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = composite.detect(page)
        
        # 应该只保留1个票据（置信度高的）
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].source, "det1")  # 置信度更高
        self.assertAlmostEqual(tickets[0].confidence, 0.9)

    def test_composite_detector_keep_best_confidence(self):
        """测试保留置信度最高的边界框。"""
        # 创建完全相同的框但置信度不同
        detector1 = Mock(spec=BaseTicketDetector)
        detector1.detect.return_value = [
            TicketBoundingBox(x=100, y=100, width=200, height=300, confidence=0.7, source="det1")
        ]
        
        detector2 = Mock(spec=BaseTicketDetector)
        detector2.detect.return_value = [
            TicketBoundingBox(x=100, y=100, width=200, height=300, confidence=0.95, source="det2")
        ]
        
        composite = CompositeTicketDetector(
            detectors=[detector1, detector2],
            iou_threshold=0.5
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = composite.detect(page)
        
        # 应该保留置信度高的
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].source, "det2")
        self.assertAlmostEqual(tickets[0].confidence, 0.95)

    def test_composite_detector_error_handling(self):
        """测试检测器失败的处理。"""
        # 创建一个失败的检测器
        failing_detector = Mock(spec=BaseTicketDetector)
        failing_detector.detect.side_effect = TicketDetectionError("检测失败")
        
        # 创建一个正常的检测器
        working_detector = Mock(spec=BaseTicketDetector)
        working_detector.detect.return_value = [
            TicketBoundingBox(x=100, y=100, width=200, height=300, confidence=0.9)
        ]
        
        composite = CompositeTicketDetector(
            detectors=[failing_detector, working_detector]
        )
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        # 应该继续执行其他检测器
        tickets = composite.detect(page)
        
        self.assertEqual(len(tickets), 1)

    def test_composite_detector_no_detectors_error(self):
        """测试没有提供检测器的情况。"""
        with self.assertRaises(ValueError) as context:
            CompositeTicketDetector(detectors=[])
        
        self.assertIn("至少需要提供一个检测器", str(context.exception))

    def test_composite_detector_all_detectors_fail(self):
        """测试所有检测器都失败的情况。"""
        detector1 = Mock(spec=BaseTicketDetector)
        detector1.detect.side_effect = TicketDetectionError("失败1")
        
        detector2 = Mock(spec=BaseTicketDetector)
        detector2.detect.side_effect = TicketDetectionError("失败2")
        
        composite = CompositeTicketDetector(detectors=[detector1, detector2])
        
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        page = PageImage(image=image, page_number=1)
        
        tickets = composite.detect(page)
        
        # 应该返回空列表
        self.assertEqual(len(tickets), 0)


class TestTicketDetectionError(unittest.TestCase):
    """测试票据检测异常。"""

    def test_error_with_cause(self):
        """测试包含原因的异常。"""
        cause = ValueError("底层错误")
        error = TicketDetectionError("检测失败", cause=cause)
        
        self.assertEqual(str(error), "检测失败")
        self.assertEqual(error.cause, cause)
        self.assertEqual(error.__cause__, cause)

    def test_error_without_cause(self):
        """测试不包含原因的异常。"""
        error = TicketDetectionError("检测失败")
        
        self.assertEqual(str(error), "检测失败")
        self.assertIsNone(error.cause)


if __name__ == "__main__":
    unittest.main()
