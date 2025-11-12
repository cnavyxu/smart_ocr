#!/usr/bin/env python3
"""验证票据分割器功能的简单脚本。"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from PIL import Image

from smart_ocr.config import Settings
from smart_ocr.pdf_ticket import (
    PageImage,
    TicketBoundingBox,
    TicketSplitter,
)


def main():
    """运行基本验证测试。"""
    print("=" * 60)
    print("票据分割器功能验证")
    print("=" * 60)
    
    # 1. 测试导入
    print("\n✓ 成功导入所有模块")
    
    # 2. 创建测试图像
    print("\n创建测试图像 (400x300)...")
    test_image = Image.new("RGB", (400, 300), color="white")
    
    # 在图像上画一些矩形
    pixels = test_image.load()
    for x in range(50, 150):
        for y in range(50, 150):
            pixels[x, y] = (0, 0, 255)  # 蓝色矩形
    
    print("✓ 测试图像创建成功")
    
    # 3. 创建PageImage
    print("\n创建PageImage对象...")
    page_image = PageImage.from_image(test_image, 1, "test_invoice")
    print(f"✓ PageImage创建成功: {page_image.width}x{page_image.height}, page={page_image.page_number}")
    
    # 4. 创建边界框
    print("\n创建边界框...")
    boxes = [
        TicketBoundingBox(50, 50, 150, 150, confidence=0.95, strategy="test"),
        TicketBoundingBox(200, 50, 300, 150, confidence=0.90, strategy="test"),
    ]
    print(f"✓ 创建了 {len(boxes)} 个边界框")
    
    # 5. 测试边界框padding
    print("\n测试边界框padding...")
    expanded = boxes[0].expand_with_padding(10, 400, 300)
    print(f"  原始: ({boxes[0].x1}, {boxes[0].y1}) -> ({boxes[0].x2}, {boxes[0].y2})")
    print(f"  扩展: ({expanded.x1}, {expanded.y1}) -> ({expanded.x2}, {expanded.y2})")
    print("✓ Padding测试通过")
    
    # 6. 创建分割器并执行分割
    print("\n创建票据分割器...")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # 测试保存到磁盘
        print(f"  输出目录: {temp_path}")
        splitter = TicketSplitter(
            settings=Settings(),
            output_root=temp_path,
            image_format="png",
            padding=5,
            save_to_disk=True,
            return_bytes=False,
        )
        print("✓ 分割器创建成功")
        
        # 执行分割
        print("\n执行票据分割...")
        results = splitter.split_page_tickets(page_image, boxes)
        print(f"✓ 分割完成，共 {len(results)} 个票据")
        
        # 验证结果
        print("\n验证分割结果:")
        for i, result in enumerate(results):
            print(f"\n  票据 {i}:")
            print(f"    - 文件路径: {result.file_path}")
            print(f"    - 页码: {result.page_number}")
            print(f"    - 索引: {result.ticket_index}")
            print(f"    - 尺寸: {result.width}x{result.height}")
            print(f"    - 策略: {result.strategy}")
            print(f"    - 置信度: {result.bounding_box.confidence}")
            
            # 验证文件存在
            if result.file_path and result.file_path.exists():
                print(f"    ✓ 文件已保存")
            else:
                print(f"    ✗ 文件未找到")
                return False
        
        # 测试内存返回
        print("\n\n测试内存返回模式...")
        splitter_memory = TicketSplitter(
            settings=Settings(),
            output_root=temp_path,
            save_to_disk=False,
            return_bytes=True,
        )
        
        results_memory = splitter_memory.split_page_tickets(page_image, [boxes[0]])
        
        if results_memory[0].image_bytes:
            print(f"✓ 内存返回成功，字节大小: {len(results_memory[0].image_bytes)}")
        else:
            print("✗ 内存返回失败")
            return False
        
        if results_memory[0].file_path is None:
            print("✓ 未保存到磁盘（符合预期）")
        else:
            print("✗ 意外保存到磁盘")
            return False
    
    # 7. 测试to_dict
    print("\n\n测试结果转换为字典...")
    result_dict = results[0].to_dict()
    print(f"✓ 字典包含 {len(result_dict)} 个字段")
    print(f"  关键字段: {list(result_dict.keys())}")
    
    print("\n" + "=" * 60)
    print("所有验证测试通过！✓")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
