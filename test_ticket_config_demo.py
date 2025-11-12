#!/usr/bin/env python3
"""票据配置功能演示脚本。

该脚本演示如何使用新增的票据配置和数据模型。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from smart_ocr.config import get_settings
from smart_ocr.pdf_ticket import PageImage, TicketBoundingBox, TicketSplitResult


def main():
    """主函数，演示票据配置和模型的使用。"""
    print("=" * 60)
    print("票据配置与模型功能演示")
    print("=" * 60)
    print()

    # 1. 获取并显示配置
    print("1. 票据检测配置:")
    print("-" * 60)
    settings = get_settings()
    print(f"   检测策略: {settings.ticket_detection_strategies}")
    print(f"   允许OCR检测: {settings.ticket_allow_ocr_detection}")
    print(f"   允许轮廓检测: {settings.ticket_allow_contour_detection}")
    print(f"   最小面积阈值: {settings.ticket_detection_min_area} 平方像素")
    print(f"   最小文本字符数: {settings.ticket_detection_min_text}")
    print(f"   输出根目录: {settings.ticket_output_root}")
    print(f"   留白像素数: {settings.ticket_padding_pixels}")
    print()

    # 2. 创建页面图像模型
    print("2. 创建页面图像模型:")
    print("-" * 60)
    page = PageImage(
        page_number=1,
        width=1920,
        height=1080,
        dpi=settings.pdf_render_dpi,
        image_data="/path/to/page1.png"
    )
    print(f"   页码: {page.page_number}")
    print(f"   尺寸: {page.width}x{page.height}")
    print(f"   DPI: {page.dpi}")
    print(f"   图像数据: {page.image_data}")
    print()

    # 3. 创建票据边界框模型
    print("3. 创建票据边界框模型:")
    print("-" * 60)
    bbox = TicketBoundingBox(
        x1=100.0,
        y1=200.0,
        x2=800.0,
        y2=900.0,
        confidence=0.95,
        source_strategy="ocr",
        page_number=page.page_number
    )
    print(f"   左上角: ({bbox.x1}, {bbox.y1})")
    print(f"   右下角: ({bbox.x2}, {bbox.y2})")
    print(f"   置信度: {bbox.confidence}")
    print(f"   检测策略: {bbox.source_strategy}")
    print(f"   所在页码: {bbox.page_number}")
    width, height = bbox.get_dimensions()
    print(f"   尺寸: {width}x{height}")
    print(f"   面积: {bbox.get_area()} 平方像素")
    print()

    # 4. 创建票据拆分结果模型
    print("4. 创建票据拆分结果模型:")
    print("-" * 60)
    result = TicketSplitResult(
        output_path=os.path.join(
            settings.ticket_output_root,
            f"ticket_page{page.page_number}_0.png"
        ),
        ticket_index=0,
        source_page=page.page_number,
        bounding_box=bbox,
        width=int(width),
        height=int(height)
    )
    print(f"   输出路径: {result.output_path}")
    print(f"   票据索引: {result.ticket_index}")
    print(f"   来源页码: {result.source_page}")
    print(f"   尺寸: {result.width}x{result.height}")
    print(f"   边界框置信度: {result.bounding_box.confidence}")
    print()

    print("=" * 60)
    print("演示完成！所有功能正常工作。")
    print("=" * 60)


if __name__ == "__main__":
    main()
