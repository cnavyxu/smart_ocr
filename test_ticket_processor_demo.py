#!/usr/bin/env python
"""PDF票据处理器演示脚本。

展示如何使用PDFTicketProcessor处理PDF文件，包括：
1. 基本的PDF加载和票据检测
2. 使用简单检测器（整页作为一张票据）
3. 使用组合检测器处理多个检测策略
4. 不保存到磁盘的处理模式
"""

import io
import sys
import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from smart_ocr.config import Settings
from smart_ocr.pdf_ticket import (
    BoundingBox,
    CompositeDetector,
    PDFTicketProcessor,
    PDFTicketProcessingError,
    TicketDetectionResult,
)
from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter


class SimpleDetector:
    """简单检测器：将整个页面作为一张票据。"""
    
    def detect(self, image, page_number=1):
        """检测票据区域（返回整个页面）。"""
        bbox = BoundingBox(
            x=0,
            y=0,
            width=image.width,
            height=image.height,
            confidence=1.0,
        )
        return TicketDetectionResult(
            page_number=page_number,
            bounding_boxes=[bbox],
        )


class GridDetector:
    """网格检测器：将页面分割为网格。"""
    
    def __init__(self, rows=2, cols=2):
        """初始化网格检测器。
        
        参数:
            rows: 行数
            cols: 列数
        """
        self.rows = rows
        self.cols = cols
    
    def detect(self, image, page_number=1):
        """检测票据区域（网格分割）。"""
        width = image.width
        height = image.height
        
        cell_width = width // self.cols
        cell_height = height // self.rows
        
        boxes = []
        for row in range(self.rows):
            for col in range(self.cols):
                bbox = BoundingBox(
                    x=col * cell_width,
                    y=row * cell_height,
                    width=cell_width,
                    height=cell_height,
                    confidence=0.9,
                )
                boxes.append(bbox)
        
        return TicketDetectionResult(
            page_number=page_number,
            bounding_boxes=boxes,
        )


def create_sample_pdf(num_pages=3):
    """创建一个示例PDF文件用于测试。
    
    参数:
        num_pages: 页数
    
    返回:
        PDF文件的字节流
    """
    print(f"📄 创建包含{num_pages}页的示例PDF...")
    
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    
    for i in range(num_pages):
        # 绘制页面内容
        c.setFont("Helvetica", 24)
        c.drawString(100, 750, f"Page {i + 1}")
        
        # 绘制一些票据样式的矩形
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"Sample ticket content on page {i + 1}")
        c.rect(80, 650, 200, 100)
        
        c.showPage()
    
    c.save()
    pdf_bytes = pdf_buffer.getvalue()
    
    print(f"✅ 示例PDF创建完成（{len(pdf_bytes)} 字节）\n")
    return pdf_bytes


def demo_basic_processing():
    """演示1：基本的PDF票据处理流程。"""
    print("=" * 60)
    print("演示1：基本的PDF票据处理流程")
    print("=" * 60)
    
    # 创建配置
    settings = Settings(pdf_render_dpi=150)
    
    # 创建检测器和拆分器
    detector = SimpleDetector()
    splitter = SimpleTicketSplitter(image_format="PNG")
    
    # 创建处理器
    processor = PDFTicketProcessor(
        settings=settings,
        detector=detector,
        splitter=splitter,
        save_to_disk=True,
    )
    
    # 创建示例PDF
    pdf_bytes = create_sample_pdf(num_pages=2)
    
    # 处理PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "tickets"
        
        print("🔄 开始处理PDF...")
        try:
            results = processor.process_pdf(pdf_bytes, output_dir=output_dir)
            
            print(f"✅ 处理完成！\n")
            print(f"📊 结果统计:")
            print(f"  - 总页数: {len(results)}")
            print(f"  - 总票据数: {sum(r.ticket_count for r in results)}")
            print()
            
            for result in results:
                print(f"  第{result.page_number}页:")
                print(f"    - 票据数量: {result.ticket_count}")
                if result.split_time:
                    print(f"    - 拆分耗时: {result.split_time:.3f}秒")
                
                for ticket in result.tickets:
                    print(f"      ✓ {ticket.saved_path.name}")
            
            print()
            
        except PDFTicketProcessingError as e:
            print(f"❌ 处理失败: {e}")
            print(f"   阶段: {e.stage}")
            sys.exit(1)


def demo_grid_detection():
    """演示2：使用网格检测器处理PDF。"""
    print("=" * 60)
    print("演示2：使用网格检测器拆分页面")
    print("=" * 60)
    
    settings = Settings(pdf_render_dpi=150)
    
    # 使用网格检测器（2x2网格）
    detector = GridDetector(rows=2, cols=2)
    splitter = SimpleTicketSplitter(image_format="PNG")
    
    processor = PDFTicketProcessor(
        settings=settings,
        detector=detector,
        splitter=splitter,
        save_to_disk=True,
    )
    
    pdf_bytes = create_sample_pdf(num_pages=1)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "grid_tickets"
        
        print("🔄 使用2x2网格检测器处理PDF...")
        results = processor.process_pdf(pdf_bytes, output_dir=output_dir)
        
        print(f"✅ 处理完成！\n")
        print(f"📊 从1页中拆分出{results[0].ticket_count}张票据（2x2网格）")
        print()


def demo_composite_detector():
    """演示3：使用组合检测器。"""
    print("=" * 60)
    print("演示3：使用组合检测器")
    print("=" * 60)
    
    settings = Settings(pdf_render_dpi=150)
    
    # 创建两个不同的检测器
    detector1 = SimpleDetector()
    detector2 = GridDetector(rows=1, cols=2)
    
    # 组合检测器
    composite = CompositeDetector([detector1, detector2])
    splitter = SimpleTicketSplitter(image_format="PNG")
    
    processor = PDFTicketProcessor(
        settings=settings,
        detector=composite,
        splitter=splitter,
        save_to_disk=True,
    )
    
    pdf_bytes = create_sample_pdf(num_pages=1)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "composite_tickets"
        
        print("🔄 使用组合检测器处理PDF（整页 + 1x2网格）...")
        results = processor.process_pdf(pdf_bytes, output_dir=output_dir)
        
        print(f"✅ 处理完成！\n")
        print(f"📊 检测器1找到1个区域，检测器2找到2个区域")
        print(f"   总计: {results[0].ticket_count}张票据")
        print()


def demo_no_save():
    """演示4：不保存到磁盘的处理模式。"""
    print("=" * 60)
    print("演示4：不保存到磁盘（仅内存处理）")
    print("=" * 60)
    
    settings = Settings(pdf_render_dpi=150)
    
    detector = SimpleDetector()
    splitter = SimpleTicketSplitter(image_format="PNG")
    
    # 设置save_to_disk=False
    processor = PDFTicketProcessor(
        settings=settings,
        detector=detector,
        splitter=splitter,
        save_to_disk=False,  # 不保存
    )
    
    pdf_bytes = create_sample_pdf(num_pages=2)
    
    print("🔄 处理PDF（仅保存在内存中）...")
    results = processor.process_pdf(pdf_bytes)
    
    print(f"✅ 处理完成！\n")
    print(f"📊 结果统计:")
    print(f"  - 总票据数: {sum(r.ticket_count for r in results)}")
    print()
    
    for result in results:
        for ticket in result.tickets:
            print(f"  第{ticket.page_number}页票据{ticket.ticket_index}:")
            print(f"    - 图像尺寸: {ticket.image.width}x{ticket.image.height}")
            print(f"    - 边界框: ({ticket.bbox.x}, {ticket.bbox.y}, "
                  f"{ticket.bbox.width}, {ticket.bbox.height})")
            print(f"    - 保存路径: {ticket.saved_path or '未保存'}")
    
    print()


def demo_error_handling():
    """演示5：异常处理。"""
    print("=" * 60)
    print("演示5：异常处理")
    print("=" * 60)
    
    settings = Settings(pdf_render_dpi=150)
    
    detector = SimpleDetector()
    splitter = SimpleTicketSplitter()
    
    processor = PDFTicketProcessor(
        settings=settings,
        detector=detector,
        splitter=splitter,
        save_to_disk=True,
    )
    
    print("🔄 尝试处理无效PDF...")
    try:
        # 提供无效的PDF数据
        processor.process_pdf(b"not a pdf", output_dir=Path("/tmp/output"))
    except PDFTicketProcessingError as e:
        print(f"✅ 捕获到预期的异常:")
        print(f"   消息: {e.message}")
        print(f"   阶段: {e.stage}")
        print(f"   原始错误: {type(e.original_error).__name__}")
    
    print()


def main():
    """运行所有演示。"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "PDF票据处理器演示脚本" + " " * 28 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    try:
        demo_basic_processing()
        demo_grid_detection()
        demo_composite_detector()
        demo_no_save()
        demo_error_handling()
        
        print("=" * 60)
        print("🎉 所有演示完成！")
        print("=" * 60)
        print()
        
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
