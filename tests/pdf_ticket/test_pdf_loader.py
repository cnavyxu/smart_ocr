"""PDF加载器的单元测试。

测试pdf_loader模块的各项功能，包括正常场景和异常场景。
使用PyMuPDF动态生成测试PDF文档。
"""

import io
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from smart_ocr.pdf_ticket.pdf_loader import (
    PDFLoadError,
    PageImage,
    load_pdf_from_bytes,
    load_pdf_from_path,
    load_pdf_to_images,
)


def create_test_pdf(page_count: int = 2, page_size: tuple = (595, 842)) -> bytes:
    """动态创建测试用的PDF文档。
    
    参数:
        page_count: PDF页数
        page_size: 页面尺寸（宽度, 高度），默认为A4尺寸（595x842点）
    
    返回:
        PDF文件的二进制数据
    """
    doc = fitz.open()
    
    for i in range(page_count):
        page = doc.new_page(width=page_size[0], height=page_size[1])
        
        text = f"这是第 {i + 1} 页"
        text_point = fitz.Point(100, 100)
        page.insert_text(text_point, text, fontsize=20)
        
        rect = fitz.Rect(50, 50, 250, 200)
        page.draw_rect(rect, color=(0, 0, 1), width=2)
        
        circle_center = fitz.Point(400, 400)
        page.draw_circle(circle_center, 50, color=(1, 0, 0), width=2)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


def create_corrupted_pdf() -> bytes:
    """创建损坏的PDF数据用于异常测试。
    
    返回:
        无效的PDF字节数据
    """
    return b"This is not a valid PDF file content"


class TestLoadPdfFromBytes:
    """测试load_pdf_from_bytes函数。"""
    
    def test_load_valid_pdf_default_dpi(self):
        """测试使用默认DPI加载有效的PDF字节流。"""
        pdf_bytes = create_test_pdf(page_count=2)
        
        pages = load_pdf_from_bytes(pdf_bytes)
        
        assert len(pages) == 2
        assert all(isinstance(page, PageImage) for page in pages)
        
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2
        
        for page in pages:
            assert page.width > 0
            assert page.height > 0
            assert page.dpi == 220
            assert page.format == "PNG"
            assert page.image is not None
            assert len(page.image_bytes) > 0
    
    def test_load_valid_pdf_custom_dpi(self):
        """测试使用自定义DPI加载PDF。"""
        pdf_bytes = create_test_pdf(page_count=3)
        custom_dpi = 150
        
        pages = load_pdf_from_bytes(pdf_bytes, dpi=custom_dpi)
        
        assert len(pages) == 3
        
        for page in pages:
            assert page.dpi == custom_dpi
    
    def test_load_pdf_jpeg_format(self):
        """测试输出为JPEG格式。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        pages = load_pdf_from_bytes(pdf_bytes, output_format="JPEG")
        
        assert len(pages) == 1
        assert pages[0].format == "JPEG"
    
    def test_load_pdf_jpg_format_alias(self):
        """测试JPG作为JPEG的别名。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        pages = load_pdf_from_bytes(pdf_bytes, output_format="JPG")
        
        assert len(pages) == 1
        assert pages[0].format == "JPEG"
    
    def test_empty_pdf_bytes(self):
        """测试空字节流抛出异常。"""
        with pytest.raises(PDFLoadError, match="PDF字节流为空"):
            load_pdf_from_bytes(b"")
    
    def test_corrupted_pdf_bytes(self):
        """测试损坏的PDF字节流抛出异常。"""
        corrupted_bytes = create_corrupted_pdf()
        
        with pytest.raises(PDFLoadError, match="无法打开PDF文档，可能文件已损坏"):
            load_pdf_from_bytes(corrupted_bytes)
    
    def test_invalid_output_format(self):
        """测试不支持的输出格式抛出异常。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        with pytest.raises(ValueError, match="不支持的输出格式"):
            load_pdf_from_bytes(pdf_bytes, output_format="BMP")
    
    def test_resolution_consistency(self):
        """测试图像分辨率与DPI的一致性。"""
        pdf_bytes = create_test_pdf(page_count=1, page_size=(595, 842))
        dpi = 300
        
        pages = load_pdf_from_bytes(pdf_bytes, dpi=dpi)
        
        assert len(pages) == 1
        page = pages[0]
        
        expected_width = int(595 * dpi / 72.0)
        expected_height = int(842 * dpi / 72.0)
        
        assert abs(page.width - expected_width) <= 2
        assert abs(page.height - expected_height) <= 2
    
    def test_save_to_disk(self):
        """测试保存图像到磁盘功能。"""
        pdf_bytes = create_test_pdf(page_count=2)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pages = load_pdf_from_bytes(
                pdf_bytes,
                save_to_disk=True,
                save_dir=temp_dir,
            )
            
            assert len(pages) == 2
            
            page1_path = Path(temp_dir) / "page_1.png"
            page2_path = Path(temp_dir) / "page_2.png"
            
            assert page1_path.exists()
            assert page2_path.exists()
            
            assert page1_path.stat().st_size > 0
            assert page2_path.stat().st_size > 0


class TestLoadPdfFromPath:
    """测试load_pdf_from_path函数。"""
    
    def test_load_from_valid_path(self):
        """测试从有效文件路径加载PDF。"""
        pdf_bytes = create_test_pdf(page_count=2)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        try:
            pages = load_pdf_from_path(tmp_path)
            
            assert len(pages) == 2
            assert all(isinstance(page, PageImage) for page in pages)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_load_from_path_object(self):
        """测试使用Path对象加载PDF。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = Path(tmp_file.name)
        
        try:
            pages = load_pdf_from_path(tmp_path)
            
            assert len(pages) == 1
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def test_nonexistent_file(self):
        """测试不存在的文件路径抛出异常。"""
        with pytest.raises(PDFLoadError, match="PDF文件不存在"):
            load_pdf_from_path("/nonexistent/path/file.pdf")
    
    def test_path_is_directory(self):
        """测试路径是目录时抛出异常。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(PDFLoadError, match="路径不是文件"):
                load_pdf_from_path(temp_dir)


class TestLoadPdfToImages:
    """测试load_pdf_to_images统一入口函数。"""
    
    def test_load_from_bytes(self):
        """测试从字节流加载。"""
        pdf_bytes = create_test_pdf(page_count=2)
        
        pages = load_pdf_to_images(pdf_bytes)
        
        assert len(pages) == 2
    
    def test_load_from_string_path(self):
        """测试从字符串路径加载。"""
        pdf_bytes = create_test_pdf(page_count=2)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        try:
            pages = load_pdf_to_images(tmp_path)
            
            assert len(pages) == 2
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_load_from_path_object(self):
        """测试从Path对象加载。"""
        pdf_bytes = create_test_pdf(page_count=2)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = Path(tmp_file.name)
        
        try:
            pages = load_pdf_to_images(tmp_path)
            
            assert len(pages) == 2
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def test_invalid_source_type(self):
        """测试不支持的数据源类型抛出异常。"""
        with pytest.raises(ValueError, match="不支持的pdf_source类型"):
            load_pdf_to_images(12345)
    
    def test_with_custom_parameters(self):
        """测试传递自定义参数。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        pages = load_pdf_to_images(
            pdf_bytes,
            dpi=200,
            output_format="JPEG",
        )
        
        assert len(pages) == 1
        assert pages[0].dpi == 200
        assert pages[0].format == "JPEG"


class TestPageImageDataClass:
    """测试PageImage数据类。"""
    
    def test_page_image_attributes(self):
        """测试PageImage对象的所有属性。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        pages = load_pdf_from_bytes(pdf_bytes, dpi=150)
        
        assert len(pages) == 1
        page = pages[0]
        
        assert hasattr(page, "page_number")
        assert hasattr(page, "image")
        assert hasattr(page, "image_bytes")
        assert hasattr(page, "width")
        assert hasattr(page, "height")
        assert hasattr(page, "dpi")
        assert hasattr(page, "format")
        
        assert page.page_number == 1
        assert page.dpi == 150
        assert page.width > 0
        assert page.height > 0


class TestEdgeCases:
    """测试边界情况和特殊场景。"""
    
    def test_single_page_pdf(self):
        """测试单页PDF。"""
        pdf_bytes = create_test_pdf(page_count=1)
        
        pages = load_pdf_from_bytes(pdf_bytes)
        
        assert len(pages) == 1
        assert pages[0].page_number == 1
    
    def test_many_pages_pdf(self):
        """测试多页PDF。"""
        pdf_bytes = create_test_pdf(page_count=10)
        
        pages = load_pdf_from_bytes(pdf_bytes)
        
        assert len(pages) == 10
        
        for i, page in enumerate(pages, start=1):
            assert page.page_number == i
    
    def test_different_page_sizes(self):
        """测试不同页面尺寸的PDF。"""
        doc = fitz.open()
        
        doc.new_page(width=595, height=842)
        
        doc.new_page(width=420, height=595)
        
        pdf_bytes = doc.tobytes()
        doc.close()
        
        pages = load_pdf_from_bytes(pdf_bytes)
        
        assert len(pages) == 2
        assert pages[0].width != pages[1].width or pages[0].height != pages[1].height
