#!/usr/bin/env python
"""票据检测器使用示例。

本脚本演示如何使用各种票据检测器来检测图像中的票据区域。
"""

import logging

import cv2
import numpy as np

from src.smart_ocr.pdf_ticket.ticket_detector import (
    CompositeTicketDetector,
    ContourTicketDetector,
    OCRTextTicketDetector,
    PageImage,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def create_sample_image():
    """创建一个包含票据的示例图像。
    
    Returns:
        示例图像（NumPy数组）
    """
    # 创建白色背景
    image = np.ones((800, 1200, 3), dtype=np.uint8) * 255
    
    # 绘制两个模拟票据（黑色矩形）
    cv2.rectangle(image, (100, 100), (400, 350), (0, 0, 0), 3)
    cv2.rectangle(image, (500, 150), (900, 450), (0, 0, 0), 3)
    
    # 在票据内部添加一些文字区域（模拟OCR检测结果）
    for y in range(120, 330, 40):
        cv2.rectangle(image, (120, y), (380, y + 20), (100, 100, 100), -1)
    
    for y in range(170, 430, 40):
        cv2.rectangle(image, (520, y), (880, y + 20), (100, 100, 100), -1)
    
    return image


def mock_ocr_detector(image: np.ndarray):
    """模拟OCR检测器，返回文本框列表。
    
    Args:
        image: 输入图像
        
    Returns:
        文本框列表，每个框由4个顶点坐标组成
    """
    # 返回模拟的文本框（对应我们在示例图像中绘制的矩形）
    text_boxes = []
    
    # 第一个票据区域的文本框
    for y in range(120, 330, 40):
        text_boxes.append([
            [120, y], [380, y], [380, y + 20], [120, y + 20]
        ])
    
    # 第二个票据区域的文本框
    for y in range(170, 430, 40):
        text_boxes.append([
            [520, y], [880, y], [880, y + 20], [520, y + 20]
        ])
    
    return text_boxes


def example_ocr_detector():
    """示例：使用OCR文本检测器。"""
    print("\n" + "=" * 70)
    print("示例 1: OCR文本检测器")
    print("=" * 70)
    
    # 创建检测器
    detector = OCRTextTicketDetector(
        ocr_detector=mock_ocr_detector,
        min_text_boxes=3,
        min_area=5000,
        eps=50.0,
        min_samples=2
    )
    
    # 创建示例图像
    image = create_sample_image()
    page = PageImage(image=image, page_number=1)
    
    # 执行检测
    tickets = detector.detect(page)
    
    # 打印结果
    print(f"\n检测到 {len(tickets)} 个票据:")
    for i, ticket in enumerate(tickets, 1):
        print(f"\n票据 {i}:")
        print(f"  位置: ({ticket.x}, {ticket.y})")
        print(f"  尺寸: {ticket.width} x {ticket.height}")
        print(f"  面积: {ticket.area()} 像素")
        print(f"  置信度: {ticket.confidence:.2f}")
        print(f"  来源: {ticket.source}")


def example_contour_detector():
    """示例：使用轮廓检测器。"""
    print("\n" + "=" * 70)
    print("示例 2: 轮廓检测器")
    print("=" * 70)
    
    # 创建检测器
    detector = ContourTicketDetector(
        min_area=5000,
        max_area=0.9,
        canny_threshold1=50,
        canny_threshold2=150
    )
    
    # 创建示例图像
    image = create_sample_image()
    page = PageImage(image=image, page_number=1)
    
    # 执行检测
    tickets = detector.detect(page)
    
    # 打印结果
    print(f"\n检测到 {len(tickets)} 个票据:")
    for i, ticket in enumerate(tickets, 1):
        print(f"\n票据 {i}:")
        print(f"  位置: ({ticket.x}, {ticket.y})")
        print(f"  尺寸: {ticket.width} x {ticket.height}")
        print(f"  面积: {ticket.area()} 像素")
        print(f"  置信度: {ticket.confidence:.2f}")
        print(f"  来源: {ticket.source}")


def example_composite_detector():
    """示例：使用组合检测器。"""
    print("\n" + "=" * 70)
    print("示例 3: 组合检测器")
    print("=" * 70)
    
    # 创建多个检测器
    ocr_detector = OCRTextTicketDetector(
        ocr_detector=mock_ocr_detector,
        min_text_boxes=3,
        min_area=5000
    )
    
    contour_detector = ContourTicketDetector(
        min_area=5000,
        max_area=0.9
    )
    
    # 创建组合检测器
    composite_detector = CompositeTicketDetector(
        detectors=[ocr_detector, contour_detector],
        iou_threshold=0.5
    )
    
    # 创建示例图像
    image = create_sample_image()
    page = PageImage(image=image, page_number=1)
    
    # 执行检测
    tickets = composite_detector.detect(page)
    
    # 打印结果
    print(f"\n检测到 {len(tickets)} 个票据（去重后）:")
    for i, ticket in enumerate(tickets, 1):
        print(f"\n票据 {i}:")
        print(f"  位置: ({ticket.x}, {ticket.y})")
        print(f"  尺寸: {ticket.width} x {ticket.height}")
        print(f"  面积: {ticket.area()} 像素")
        print(f"  置信度: {ticket.confidence:.2f}")
        print(f"  来源: {ticket.source}")


def main():
    """主函数。"""
    print("\n" + "=" * 70)
    print("票据检测器使用示例")
    print("=" * 70)
    
    # 运行各个示例
    example_ocr_detector()
    example_contour_detector()
    example_composite_detector()
    
    print("\n" + "=" * 70)
    print("所有示例执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
