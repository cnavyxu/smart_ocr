"""票据分割器的单元测试。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from smart_ocr.config import Settings
from smart_ocr.pdf_ticket.models import (
    PageImage,
    TicketBoundingBox,
    TicketSplitError,
)
from smart_ocr.pdf_ticket.ticket_splitter import (
    TicketSplitter,
    generate_ticket_filename,
)


class TestGenerateTicketFilename:
    """测试票据文件名生成函数。"""
    
    def test_default_format(self):
        """测试默认PNG格式的文件名生成。"""
        filename = generate_ticket_filename(1, 0)
        assert filename == "page_1_ticket_0.png"
    
    def test_custom_format(self):
        """测试自定义格式的文件名生成。"""
        filename = generate_ticket_filename(3, 5, "jpg")
        assert filename == "page_3_ticket_5.jpg"
    
    def test_large_numbers(self):
        """测试大页码和索引的文件名生成。"""
        filename = generate_ticket_filename(100, 999)
        assert filename == "page_100_ticket_999.png"


class TestTicketBoundingBox:
    """测试票据边界框模型。"""
    
    def test_get_width(self):
        """测试获取边界框宽度。"""
        box = TicketBoundingBox(10, 20, 110, 120)
        assert box.get_width() == 100
    
    def test_get_height(self):
        """测试获取边界框高度。"""
        box = TicketBoundingBox(10, 20, 110, 120)
        assert box.get_height() == 100
    
    def test_expand_with_padding_no_boundary(self):
        """测试padding扩展，不越界的情况。"""
        box = TicketBoundingBox(50, 50, 150, 150)
        expanded = box.expand_with_padding(10, 300, 300)
        
        assert expanded.x1 == 40
        assert expanded.y1 == 40
        assert expanded.x2 == 160
        assert expanded.y2 == 160
    
    def test_expand_with_padding_left_top_boundary(self):
        """测试padding扩展，左上角越界的情况。"""
        box = TicketBoundingBox(5, 5, 50, 50)
        expanded = box.expand_with_padding(10, 300, 300)
        
        assert expanded.x1 == 0  # 不会小于0
        assert expanded.y1 == 0  # 不会小于0
        assert expanded.x2 == 60
        assert expanded.y2 == 60
    
    def test_expand_with_padding_right_bottom_boundary(self):
        """测试padding扩展，右下角越界的情况。"""
        box = TicketBoundingBox(250, 250, 295, 295)
        expanded = box.expand_with_padding(10, 300, 300)
        
        assert expanded.x1 == 240
        assert expanded.y1 == 240
        assert expanded.x2 == 300  # 不会大于图像宽度
        assert expanded.y2 == 300  # 不会大于图像高度


class TestPageImage:
    """测试页面图像模型。"""
    
    def test_from_image(self):
        """测试从PIL图像创建PageImage。"""
        # 创建测试图像
        image = Image.new("RGB", (800, 600), color="white")
        
        page_image = PageImage.from_image(image, 1, "test_pdf")
        
        assert page_image.page_number == 1
        assert page_image.pdf_name == "test_pdf"
        assert page_image.width == 800
        assert page_image.height == 600
        assert page_image.image == image


class TestTicketSplitter:
    """测试票据分割器。"""
    
    @pytest.fixture
    def settings(self):
        """创建测试配置。"""
        return Settings()
    
    @pytest.fixture
    def temp_output_dir(self):
        """创建临时输出目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def test_image(self):
        """创建测试图像：400x300的白色背景，中间有彩色矩形。"""
        image = Image.new("RGB", (400, 300), color="white")
        
        # 在图像上画一些矩形作为票据
        pixels = image.load()
        # 左上角蓝色矩形 (10, 10) -> (90, 90)
        for x in range(10, 90):
            for y in range(10, 90):
                pixels[x, y] = (0, 0, 255)
        
        # 右上角红色矩形 (210, 10) -> (290, 90)
        for x in range(210, 290):
            for y in range(10, 90):
                pixels[x, y] = (255, 0, 0)
        
        # 左下角绿色矩形 (10, 210) -> (90, 290)
        for x in range(10, 90):
            for y in range(210, 290):
                pixels[x, y] = (0, 255, 0)
        
        return image
    
    @pytest.fixture
    def test_page_image(self, test_image):
        """创建测试页面图像。"""
        return PageImage.from_image(test_image, 1, "test_invoice")
    
    def test_initialization(self, settings, temp_output_dir):
        """测试分割器初始化。"""
        splitter = TicketSplitter(
            settings=settings,
            output_root=temp_output_dir,
            image_format="png",
            padding=5,
        )
        
        assert splitter.output_root == temp_output_dir
        assert splitter.image_format == "png"
        assert splitter.padding == 5
        assert splitter.save_to_disk is True
        assert splitter.return_bytes is False
    
    def test_ensure_output_directory(self, settings, temp_output_dir):
        """测试输出目录创建。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        output_dir = splitter._ensure_output_directory("test_pdf")
        
        assert output_dir.exists()
        assert output_dir.is_dir()
        assert output_dir == temp_output_dir / "test_pdf"
    
    def test_ensure_output_directory_nested(self, settings, temp_output_dir):
        """测试嵌套目录创建。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        # 使用包含子目录的PDF名称
        output_dir = splitter._ensure_output_directory("sub/test_pdf")
        
        assert output_dir.exists()
        assert output_dir.is_dir()
    
    def test_crop_ticket_image_no_padding(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试裁剪票据图像（无padding）。"""
        splitter = TicketSplitter(settings, temp_output_dir, padding=0)
        
        box = TicketBoundingBox(10, 10, 90, 90)
        cropped = splitter._crop_ticket_image(test_page_image, box)
        
        assert cropped.size == (80, 80)  # 90-10 = 80
    
    def test_crop_ticket_image_with_padding(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试裁剪票据图像（有padding）。"""
        splitter = TicketSplitter(settings, temp_output_dir, padding=5)
        
        box = TicketBoundingBox(50, 50, 100, 100)
        cropped = splitter._crop_ticket_image(test_page_image, box)
        
        # 原始: 50x50, 加上5像素padding: (50-5)到(100+5) = 55x55
        assert cropped.size == (55, 55)
    
    def test_crop_ticket_image_with_padding_boundary(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试裁剪票据图像（padding越界）。"""
        splitter = TicketSplitter(settings, temp_output_dir, padding=20)
        
        # 边界框在图像边缘
        box = TicketBoundingBox(0, 0, 50, 50)
        cropped = splitter._crop_ticket_image(test_page_image, box)
        
        # padding=20，但左上角不会小于0，右下角可以扩展
        # x: max(0, 0-20) -> min(400, 50+20) = 0 -> 70 = 70
        # y: max(0, 0-20) -> min(300, 50+20) = 0 -> 70 = 70
        assert cropped.size == (70, 70)
    
    def test_split_page_tickets_single(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试分割单个票据。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        boxes = [TicketBoundingBox(10, 10, 90, 90, strategy="test_strategy")]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        assert len(results) == 1
        
        result = results[0]
        assert result.page_number == 1
        assert result.ticket_index == 0
        assert result.width == 80
        assert result.height == 80
        assert result.strategy == "test_strategy"
        
        # 验证文件保存
        assert result.file_path is not None
        assert result.file_path.exists()
        assert result.file_path.name == "page_1_ticket_0.png"
    
    def test_split_page_tickets_multiple(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试分割多个票据。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        boxes = [
            TicketBoundingBox(10, 10, 90, 90, strategy="strategy_1"),
            TicketBoundingBox(210, 10, 290, 90, strategy="strategy_2"),
            TicketBoundingBox(10, 210, 90, 290, strategy="strategy_3"),
        ]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        assert len(results) == 3
        
        # 验证每个结果
        for i, result in enumerate(results):
            assert result.page_number == 1
            assert result.ticket_index == i
            assert result.file_path is not None
            assert result.file_path.exists()
            assert result.file_path.name == f"page_1_ticket_{i}.png"
    
    def test_split_page_tickets_directory_structure(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试目录结构正确性。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        boxes = [TicketBoundingBox(10, 10, 90, 90)]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        result = results[0]
        expected_dir = temp_output_dir / "test_invoice"
        
        assert result.file_path.parent == expected_dir
        assert expected_dir.exists()
    
    def test_split_page_tickets_with_return_bytes(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试返回字节数据。"""
        splitter = TicketSplitter(
            settings,
            temp_output_dir,
            return_bytes=True,
        )
        
        boxes = [TicketBoundingBox(10, 10, 90, 90)]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        result = results[0]
        assert result.image_bytes is not None
        assert isinstance(result.image_bytes, bytes)
        assert len(result.image_bytes) > 0
    
    def test_split_page_tickets_memory_only(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试仅内存返回，不保存到磁盘。"""
        splitter = TicketSplitter(
            settings,
            temp_output_dir,
            save_to_disk=False,
            return_bytes=True,
        )
        
        boxes = [TicketBoundingBox(10, 10, 90, 90)]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        result = results[0]
        assert result.file_path is None
        assert result.image_bytes is not None
    
    def test_split_page_tickets_empty_boxes(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试空边界框列表。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        results = splitter.split_page_tickets(test_page_image, [])
        
        assert results == []
    
    def test_split_page_tickets_jpg_format(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试保存为JPG格式。"""
        splitter = TicketSplitter(
            settings,
            temp_output_dir,
            image_format="jpg",
        )
        
        boxes = [TicketBoundingBox(10, 10, 90, 90)]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        result = results[0]
        assert result.file_path.suffix == ".jpg"
        assert result.file_path.name == "page_1_ticket_0.jpg"
    
    def test_split_page_tickets_io_error(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试IO错误处理（只读目录）。"""
        # 创建只读目录
        readonly_dir = temp_output_dir / "readonly"
        readonly_dir.mkdir()
        
        # 使readonly_dir不可写
        os.chmod(readonly_dir, 0o444)
        
        try:
            splitter = TicketSplitter(settings, readonly_dir)
            boxes = [TicketBoundingBox(10, 10, 90, 90)]
            
            # 应该抛出TicketSplitError
            with pytest.raises(TicketSplitError) as excinfo:
                splitter.split_page_tickets(test_page_image, boxes)
            
            # 验证错误信息
            assert "创建输出目录失败" in str(excinfo.value) or "保存图像失败" in str(excinfo.value)
        
        finally:
            # 恢复权限以便清理
            os.chmod(readonly_dir, 0o755)
    
    def test_result_to_dict(self, settings, temp_output_dir, test_page_image):
        """测试结果转换为字典。"""
        splitter = TicketSplitter(settings, temp_output_dir, return_bytes=True)
        
        boxes = [
            TicketBoundingBox(
                10, 10, 90, 90,
                confidence=0.95,
                strategy="test_strategy"
            )
        ]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        result_dict = results[0].to_dict()
        
        assert result_dict["page_number"] == 1
        assert result_dict["ticket_index"] == 0
        assert result_dict["width"] == 80
        assert result_dict["height"] == 80
        assert result_dict["strategy"] == "test_strategy"
        assert result_dict["has_image_bytes"] is True
        
        bbox = result_dict["bounding_box"]
        assert bbox["x1"] == 10
        assert bbox["y1"] == 10
        assert bbox["x2"] == 90
        assert bbox["y2"] == 90
        assert bbox["confidence"] == 0.95
        assert bbox["strategy"] == "test_strategy"
    
    def test_split_with_confidence(
        self,
        settings,
        temp_output_dir,
        test_page_image,
    ):
        """测试边界框置信度保留。"""
        splitter = TicketSplitter(settings, temp_output_dir)
        
        boxes = [
            TicketBoundingBox(
                10, 10, 90, 90,
                confidence=0.85,
                strategy="model_based"
            )
        ]
        
        results = splitter.split_page_tickets(test_page_image, boxes)
        
        result = results[0]
        assert result.bounding_box.confidence == 0.85
        assert result.strategy == "model_based"
