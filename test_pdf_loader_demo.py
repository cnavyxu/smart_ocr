#!/usr/bin/env python
"""PDF加载器功能演示脚本。

演示如何使用pdf_loader模块加载和处理PDF文件。
"""

import fitz

from smart_ocr.pdf_ticket import (
    PDFLoadError,
    load_pdf_from_bytes,
    load_pdf_to_images,
)


def create_sample_pdf() -> bytes:
    """创建一个简单的示例PDF用于演示。"""
    doc = fitz.open()
    
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        text = f"示例PDF - 第 {i + 1} 页"
        page.insert_text((100, 100), text, fontsize=24)
        
        page.insert_text((100, 200), "这是一个PDF加载器功能演示", fontsize=16)
        page.insert_text((100, 250), f"当前页码: {i + 1}/3", fontsize=14)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


def main():
    """主函数。"""
    print("=" * 60)
    print("PDF加载器功能演示")
    print("=" * 60)
    
    print("\n1. 创建示例PDF...")
    pdf_bytes = create_sample_pdf()
    print(f"   ✓ 已创建PDF，大小: {len(pdf_bytes)} 字节")
    
    print("\n2. 使用默认DPI加载PDF...")
    try:
        pages = load_pdf_from_bytes(pdf_bytes)
        print(f"   ✓ 成功加载 {len(pages)} 页")
        
        for page in pages:
            print(f"   - 第 {page.page_number} 页: "
                  f"{page.width}x{page.height}px, "
                  f"DPI={page.dpi}, "
                  f"格式={page.format}")
    except PDFLoadError as e:
        print(f"   ✗ 加载失败: {e}")
        return
    
    print("\n3. 使用自定义DPI和JPEG格式...")
    try:
        pages = load_pdf_to_images(
            pdf_bytes,
            dpi=300,
            output_format="JPEG",
        )
        print(f"   ✓ 成功加载 {len(pages)} 页")
        
        for page in pages:
            print(f"   - 第 {page.page_number} 页: "
                  f"{page.width}x{page.height}px, "
                  f"DPI={page.dpi}, "
                  f"格式={page.format}, "
                  f"大小={len(page.image_bytes)} 字节")
    except PDFLoadError as e:
        print(f"   ✗ 加载失败: {e}")
        return
    
    print("\n4. 测试异常处理...")
    try:
        load_pdf_from_bytes(b"")
        print("   ✗ 应该抛出异常但没有")
    except PDFLoadError as e:
        print(f"   ✓ 正确捕获异常: {e}")
    
    try:
        load_pdf_from_bytes(b"invalid pdf data")
        print("   ✗ 应该抛出异常但没有")
    except PDFLoadError as e:
        print(f"   ✓ 正确捕获异常: 无法打开PDF文档")
    
    print("\n" + "=" * 60)
    print("演示完成！所有功能正常工作。")
    print("=" * 60)


if __name__ == "__main__":
    main()
