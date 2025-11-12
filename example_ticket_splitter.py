#!/usr/bin/env python3
"""票据分割器使用示例。

这个脚本展示了如何使用 TicketSplitter 类来分割票据图像。
"""

import sys
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PIL import Image, ImageDraw

from smart_ocr.config import Settings
from smart_ocr.pdf_ticket import (
    PageImage,
    TicketBoundingBox,
    TicketSplitter,
)


def create_demo_image() -> Image.Image:
    """创建一个包含多个票据的演示图像。
    
    Returns:
        包含多个彩色矩形（模拟票据）的PIL图像
    """
    # 创建白色背景图像
    image = Image.new("RGB", (1200, 800), color="white")
    draw = ImageDraw.Draw(image)
    
    # 绘制三个票据（彩色矩形）
    # 票据1：蓝色
    draw.rectangle([50, 50, 350, 350], fill=(100, 150, 255), outline=(0, 0, 200), width=3)
    draw.text((150, 180), "Ticket 1", fill=(255, 255, 255))
    
    # 票据2：绿色
    draw.rectangle([450, 50, 750, 350], fill=(100, 255, 150), outline=(0, 200, 0), width=3)
    draw.text((550, 180), "Ticket 2", fill=(255, 255, 255))
    
    # 票据3：红色
    draw.rectangle([850, 50, 1150, 350], fill=(255, 150, 100), outline=(200, 0, 0), width=3)
    draw.text((950, 180), "Ticket 3", fill=(255, 255, 255))
    
    # 票据4：紫色（第二行）
    draw.rectangle([50, 450, 350, 750], fill=(200, 150, 255), outline=(100, 0, 200), width=3)
    draw.text((150, 580), "Ticket 4", fill=(255, 255, 255))
    
    return image


def main():
    """运行示例。"""
    print("=" * 70)
    print("票据分割器使用示例")
    print("=" * 70)
    
    # 1. 创建演示图像
    print("\n1. 创建演示图像...")
    demo_image = create_demo_image()
    print(f"   图像尺寸: {demo_image.size}")
    
    # 2. 创建PageImage对象
    print("\n2. 创建PageImage对象...")
    page = PageImage.from_image(
        image=demo_image,
        page_number=1,
        pdf_name="demo_invoice",
    )
    print(f"   页码: {page.page_number}")
    print(f"   PDF名称: {page.pdf_name}")
    
    # 3. 定义票据边界框（模拟检测结果）
    print("\n3. 定义票据边界框...")
    boxes = [
        TicketBoundingBox(
            x1=50, y1=50, x2=350, y2=350,
            confidence=0.98,
            strategy="demo_detector",
        ),
        TicketBoundingBox(
            x1=450, y1=50, x2=750, y2=350,
            confidence=0.95,
            strategy="demo_detector",
        ),
        TicketBoundingBox(
            x1=850, y1=50, x2=1150, y2=350,
            confidence=0.92,
            strategy="demo_detector",
        ),
        TicketBoundingBox(
            x1=50, y1=450, x2=350, y2=750,
            confidence=0.89,
            strategy="demo_detector",
        ),
    ]
    print(f"   检测到 {len(boxes)} 个票据")
    
    # 4. 创建票据分割器
    print("\n4. 创建票据分割器...")
    output_dir = Path(__file__).parent / "output" / "demo_tickets"
    print(f"   输出目录: {output_dir}")
    
    splitter = TicketSplitter(
        settings=Settings(),
        output_root=output_dir,
        image_format="png",
        padding=10,  # 添加10像素padding
        save_to_disk=True,
        return_bytes=False,
    )
    print("   配置: PNG格式, 10像素padding, 保存到磁盘")
    
    # 5. 执行分割
    print("\n5. 执行票据分割...")
    results = splitter.split_page_tickets(page, boxes)
    print(f"   成功分割 {len(results)} 个票据")
    
    # 6. 显示结果
    print("\n6. 分割结果详情:")
    print("-" * 70)
    for i, result in enumerate(results):
        print(f"\n   票据 #{i + 1}:")
        print(f"   - 文件路径: {result.file_path}")
        print(f"   - 页码: {result.page_number}")
        print(f"   - 索引: {result.ticket_index}")
        print(f"   - 尺寸: {result.width} x {result.height} 像素")
        print(f"   - 检测策略: {result.strategy}")
        print(f"   - 置信度: {result.bounding_box.confidence:.2%}")
        print(f"   - 边界框: ({result.bounding_box.x1}, {result.bounding_box.y1}) -> "
              f"({result.bounding_box.x2}, {result.bounding_box.y2})")
    
    # 7. 演示不同配置
    print("\n" + "=" * 70)
    print("演示其他配置选项")
    print("=" * 70)
    
    # 内存返回模式
    print("\n7a. 内存返回模式（用于API）...")
    splitter_memory = TicketSplitter(
        settings=Settings(),
        output_root=output_dir,  # 不会使用
        save_to_disk=False,
        return_bytes=True,
    )
    
    results_memory = splitter_memory.split_page_tickets(page, [boxes[0]])
    print(f"   字节数据大小: {len(results_memory[0].image_bytes)} 字节")
    print(f"   文件路径: {results_memory[0].file_path} (未保存)")
    
    # JPG格式
    print("\n7b. JPG格式保存...")
    output_dir_jpg = Path(__file__).parent / "output" / "demo_tickets_jpg"
    splitter_jpg = TicketSplitter(
        settings=Settings(),
        output_root=output_dir_jpg,
        image_format="jpg",
        padding=20,  # 更大的padding
    )
    
    results_jpg = splitter_jpg.split_page_tickets(page, [boxes[1]])
    print(f"   保存为: {results_jpg[0].file_path}")
    
    # 8. 总结
    print("\n" + "=" * 70)
    print("示例完成！")
    print("=" * 70)
    print(f"\n查看输出文件:")
    print(f"  PNG格式: {output_dir}")
    print(f"  JPG格式: {output_dir_jpg}")
    print("\n文件结构:")
    print(f"  {output_dir}/")
    print(f"    └── demo_invoice/")
    print(f"        ├── page_1_ticket_0.png")
    print(f"        ├── page_1_ticket_1.png")
    print(f"        ├── page_1_ticket_2.png")
    print(f"        └── page_1_ticket_3.png")
    

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
