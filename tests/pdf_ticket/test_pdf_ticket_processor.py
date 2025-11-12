"""PDF票据处理器单元测试。

测试PDFTicketProcessor类的各项功能，包括流程控制、结果聚合、异常处理等。
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from PIL import Image

from smart_ocr.config import Settings
from smart_ocr.pdf_ticket import (
    BoundingBox,
    PDFTicketProcessingError,
    PDFTicketProcessor,
    TicketDetectionResult,
    TicketImage,
    TicketSplitResult,
)
from smart_ocr.pdf_ticket.pdf_loader import PageImage


class MockDetector:
    """模拟检测器，用于测试。"""
    
    def __init__(self, boxes_per_page: int = 2):
        """初始化模拟检测器。
        
        参数:
            boxes_per_page: 每页返回的边界框数量
        """
        self.boxes_per_page = boxes_per_page
        self.call_count = 0
    
    def detect(self, image: Image.Image, page_number: int = 1) -> TicketDetectionResult:
        """模拟检测过程。"""
        self.call_count += 1
        boxes = [
            BoundingBox(x=i * 100, y=i * 100, width=80, height=80, confidence=0.95)
            for i in range(self.boxes_per_page)
        ]
        return TicketDetectionResult(
            page_number=page_number,
            bounding_boxes=boxes,
            detection_time=0.1,
        )


class MockSplitter:
    """模拟拆分器，用于测试。"""
    
    def __init__(self):
        self.call_count = 0
    
    def split(
        self,
        image: Image.Image,
        bounding_boxes: List[BoundingBox],
        page_number: int = 1,
        output_dir: Optional[Path] = None,
        save_to_disk: bool = True,
    ) -> TicketSplitResult:
        """模拟拆分过程。"""
        self.call_count += 1
        tickets = [
            TicketImage(
                image=Image.new("RGB", (bbox.width, bbox.height), color="white"),
                bbox=bbox,
                page_number=page_number,
                ticket_index=idx,
                saved_path=output_dir / f"page_{page_number}_ticket_{idx}.png" if output_dir else None,
            )
            for idx, bbox in enumerate(bounding_boxes)
        ]
        return TicketSplitResult(
            page_number=page_number,
            tickets=tickets,
            split_time=0.05,
        )


class MockPDFLoader:
    """模拟PDF加载器，用于测试。"""
    
    def __init__(self, page_count: int = 2):
        """初始化模拟加载器。
        
        参数:
            page_count: 返回的页面数量
        """
        self.page_count = page_count
    
    def load(self, pdf_source, dpi: Optional[int] = None) -> List[PageImage]:
        """模拟PDF加载过程。"""
        pages = []
        for i in range(self.page_count):
            img = Image.new("RGB", (800, 600), color="white")
            # 创建字节流
            img_bytes_io = io.BytesIO()
            img.save(img_bytes_io, format="PNG")
            img_bytes = img_bytes_io.getvalue()
            
            pages.append(PageImage(
                page_number=i + 1,
                image=img,
                image_bytes=img_bytes,
                width=800,
                height=600,
                dpi=dpi or 220,
                format="PNG",
            ))
        return pages


@pytest.fixture
def settings():
    """创建测试用配置对象。"""
    return Settings(pdf_render_dpi=220)


@pytest.fixture
def mock_detector():
    """创建模拟检测器。"""
    return MockDetector(boxes_per_page=2)


@pytest.fixture
def mock_splitter():
    """创建模拟拆分器。"""
    return MockSplitter()


@pytest.fixture
def mock_pdf_loader():
    """创建模拟PDF加载器。"""
    return MockPDFLoader(page_count=2)


class TestPDFTicketProcessor:
    """PDFTicketProcessor类的单元测试。"""
    
    def test_init_with_defaults(self, settings):
        """测试使用默认参数初始化。"""
        processor = PDFTicketProcessor(settings)
        assert processor.settings == settings
        assert processor.save_to_disk is True
        assert processor.debug_mode is False
        assert processor.detector is None
        assert processor.splitter is None
    
    def test_init_with_custom_components(
        self, settings, mock_detector, mock_splitter, mock_pdf_loader
    ):
        """测试使用自定义组件初始化。"""
        processor = PDFTicketProcessor(
            settings=settings,
            detector=mock_detector,
            splitter=mock_splitter,
            pdf_loader=mock_pdf_loader,
            save_to_disk=False,
            debug_mode=True,
        )
        assert processor.detector == mock_detector
        assert processor.splitter == mock_splitter
        assert processor.pdf_loader == mock_pdf_loader
        assert processor.save_to_disk is False
        assert processor.debug_mode is True
    
    def test_process_pdf_basic_flow(
        self, settings, mock_detector, mock_splitter, mock_pdf_loader
    ):
        """测试基本的PDF处理流程。"""
        processor = PDFTicketProcessor(
            settings=settings,
            detector=mock_detector,
            splitter=mock_splitter,
            pdf_loader=mock_pdf_loader,
            save_to_disk=False,
        )
        
        results = processor.process_pdf(b"fake_pdf_data")
        
        # 验证结果
        assert len(results) == 2  # 2页
        assert all(isinstance(r, TicketSplitResult) for r in results)
        
        # 验证每页的结果
        for i, result in enumerate(results):
            assert result.page_number == i + 1
            assert result.ticket_count == 2  # 每页2张票据
        
        # 验证调用次数
        assert mock_detector.call_count == 2
        assert mock_splitter.call_count == 2
    
    def test_process_pdf_with_output_dir(
        self, settings, mock_detector, mock_splitter, mock_pdf_loader
    ):
        """测试指定输出目录的处理流程。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            
            processor = PDFTicketProcessor(
                settings=settings,
                detector=mock_detector,
                splitter=mock_splitter,
                pdf_loader=mock_pdf_loader,
                save_to_disk=True,
            )
            
            results = processor.process_pdf(b"fake_pdf_data", output_dir=output_dir)
            
            assert len(results) == 2
            assert output_dir.exists()
    
    def test_process_pdf_without_detector_raises_error(
        self, settings, mock_splitter, mock_pdf_loader
    ):
        """测试缺少检测器时抛出错误。"""
        processor = PDFTicketProcessor(
            settings=settings,
            splitter=mock_splitter,
            pdf_loader=mock_pdf_loader,
        )
        
        with pytest.raises(ValueError, match="必须提供detector"):
            processor.process_pdf(b"fake_pdf_data")
    
    def test_process_pdf_without_splitter_raises_error(
        self, settings, mock_detector, mock_pdf_loader
    ):
        """测试缺少拆分器时抛出错误。"""
        processor = PDFTicketProcessor(
            settings=settings,
            detector=mock_detector,
            pdf_loader=mock_pdf_loader,
        )
        
        with pytest.raises(ValueError, match="必须提供splitter"):
            processor.process_pdf(b"fake_pdf_data")
    
    def test_process_pdf_save_to_disk_without_output_dir_raises_error(
        self, settings, mock_detector, mock_splitter, mock_pdf_loader
    ):
        """测试save_to_disk为True但未提供output_dir时抛出错误。"""
        processor = PDFTicketProcessor(
            settings=settings,
            detector=mock_detector,
            splitter=mock_splitter,
            pdf_loader=mock_pdf_loader,
            save_to_disk=True,
        )
        
        with pytest.raises(ValueError, match="必须提供output_dir"):
            processor.process_pdf(b"fake_pdf_data")
    
    def test_process_pdf_with_temporary_detector(
        self, settings, mock_splitter, mock_pdf_loader
    ):
        """测试使用临时检测器覆盖初始化的检测器。"""
        detector1 = MockDetector(boxes_per_page=1)
        detector2 = MockDetector(boxes_per_page=3)
        
        processor = PDFTicketProcessor(
            settings=settings,
            detector=detector1,
            splitter=mock_splitter,
            pdf_loader=mock_pdf_loader,
            save_to_disk=False,
        )
        
        # 使用临时检测器
        results = processor.process_pdf(b"fake_pdf_data", detector=detector2)
        
        # 验证使用了detector2
        assert detector1.call_count == 0
        assert detector2.call_count == 2
        assert all(r.ticket_count == 3 for r in results)
    
    def test_process_pdf_loading_error(
        self, settings, mock_detector, mock_splitter
    ):
        """测试PDF加载阶段的错误处理。"""
        # 创建一个会抛出异常的加载器
        failing_loader = Mock()
        failing_loader.load.side_effect = Exception("加载失败")
        
        processor = PDFTicketProcessor(
            settings=settings,
            detector=mock_detector,
            splitter=mock_splitter,
            pdf_loader=failing_loader,
            save_to_disk=False,
        )
        
        with pytest.raises(PDFTicketProcessingError) as exc_info:
            processor.process_pdf(b"fake_pdf_data")
        
        assert exc_info.value.stage == "loading"
        assert "加载失败" in str(exc_info.value)
    
    def test_process_pdf_detection_error(
        self, settings, mock_splitter, mock_pdf_loader
    ):
        """测试票据检测阶段的错误处理。"""
        # 创建一个会抛出异常的检测器
        failing_detector = Mock()
        failing_detector.detect.side_effect = Exception("检测失败")
        
        processor = PDFTicketProcessor(
            settings=settings,
            detector=failing_detector,
            splitter=mock_splitter,
            pdf_loader=mock_pdf_loader,
            save_to_disk=False,
        )
        
        with pytest.raises(PDFTicketProcessingError) as exc_info:
            processor.process_pdf(b"fake_pdf_data")
        
        assert exc_info.value.stage == "detection"
        assert "检测失败" in str(exc_info.value)
    
    def test_process_pdf_splitting_error(
        self, settings, mock_detector, mock_pdf_loader
    ):
        """测试票据拆分阶段的错误处理。"""
        # 创建一个会抛出异常的拆分器
        failing_splitter = Mock()
        failing_splitter.split.side_effect = Exception("拆分失败")
        
        processor = PDFTicketProcessor(
            settings=settings,
            detector=mock_detector,
            splitter=failing_splitter,
            pdf_loader=mock_pdf_loader,
            save_to_disk=False,
        )
        
        with pytest.raises(PDFTicketProcessingError) as exc_info:
            processor.process_pdf(b"fake_pdf_data")
        
        assert exc_info.value.stage == "splitting"
        assert "拆分失败" in str(exc_info.value)
    
    def test_composite_detector(self, settings):
        """测试组合检测器。"""
        from smart_ocr.pdf_ticket import CompositeDetector
        
        detector1 = MockDetector(boxes_per_page=2)
        detector2 = MockDetector(boxes_per_page=3)
        
        composite = CompositeDetector([detector1, detector2])
        
        image = Image.new("RGB", (800, 600), color="white")
        result = composite.detect(image, page_number=1)
        
        # 应该合并两个检测器的结果
        assert result.ticket_count == 5  # 2 + 3
        assert detector1.call_count == 1
        assert detector2.call_count == 1
    
    def test_composite_detector_empty_list_raises_error(self):
        """测试组合检测器不接受空列表。"""
        from smart_ocr.pdf_ticket import CompositeDetector
        
        with pytest.raises(ValueError, match="检测器列表不能为空"):
            CompositeDetector([])


class TestIntegration:
    """集成测试，使用真实的PDF加载器和简单拆分器。"""
    
    def test_process_simple_pdf(self, settings):
        """测试处理简单的PDF文件。"""
        # 创建一个简单的PDF文件
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        c.drawString(100, 750, "测试页面1")
        c.showPage()
        c.drawString(100, 750, "测试页面2")
        c.showPage()
        c.save()
        pdf_bytes = pdf_buffer.getvalue()
        
        # 创建简单检测器（返回整个页面作为一个票据）
        class SimpleDetector:
            def detect(self, image: Image.Image, page_number: int = 1):
                # 返回整个图像作为一个票据
                bbox = BoundingBox(
                    x=0, y=0,
                    width=image.width,
                    height=image.height,
                    confidence=1.0,
                )
                return TicketDetectionResult(
                    page_number=page_number,
                    bounding_boxes=[bbox],
                )
        
        # 使用真实的拆分器
        from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter
        
        detector = SimpleDetector()
        splitter = SimpleTicketSplitter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "tickets"
            
            processor = PDFTicketProcessor(
                settings=settings,
                detector=detector,
                splitter=splitter,
                save_to_disk=True,
            )
            
            results = processor.process_pdf(pdf_bytes, output_dir=output_dir)
            
            # 验证结果
            assert len(results) == 2  # 2页
            assert all(r.ticket_count == 1 for r in results)  # 每页1张票据
            
            # 验证文件已保存
            assert (output_dir / "page_1_ticket_0.png").exists()
            assert (output_dir / "page_2_ticket_0.png").exists()
    
    def test_process_pdf_no_save(self, settings):
        """测试不保存到磁盘的处理流程。"""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        c.drawString(100, 750, "测试页面")
        c.showPage()
        c.save()
        pdf_bytes = pdf_buffer.getvalue()
        
        # 创建简单检测器
        class SimpleDetector:
            def detect(self, image: Image.Image, page_number: int = 1):
                bbox = BoundingBox(x=0, y=0, width=image.width, height=image.height)
                return TicketDetectionResult(
                    page_number=page_number,
                    bounding_boxes=[bbox],
                )
        
        from smart_ocr.pdf_ticket.simple_splitter import SimpleTicketSplitter
        
        processor = PDFTicketProcessor(
            settings=settings,
            detector=SimpleDetector(),
            splitter=SimpleTicketSplitter(),
            save_to_disk=False,
        )
        
        results = processor.process_pdf(pdf_bytes)
        
        # 验证结果
        assert len(results) == 1
        assert results[0].ticket_count == 1
        
        # 验证图像存在但未保存到磁盘
        ticket = results[0].tickets[0]
        assert isinstance(ticket.image, Image.Image)
        assert ticket.saved_path is None
