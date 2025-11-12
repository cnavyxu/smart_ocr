"""PDF票据模型的单元测试。

测试票据检测与拆分相关数据模型的验证逻辑和功能。
"""

import pytest

from smart_ocr.pdf_ticket.models import (
    PageImage,
    TicketBoundingBox,
    TicketSplitResult,
)


class TestPageImage:
    """PageImage模型测试类。"""

    def test_create_valid_page_image(self):
        """测试创建有效的页面图像模型。"""
        page = PageImage(
            page_number=1,
            width=1920,
            height=1080,
            dpi=220,
            image_data="/path/to/image.png"
        )
        assert page.page_number == 1
        assert page.width == 1920
        assert page.height == 1080
        assert page.dpi == 220
        assert page.image_data == "/path/to/image.png"

    def test_page_image_without_data(self):
        """测试创建不带图像数据的页面模型。"""
        page = PageImage(
            page_number=2,
            width=800,
            height=600,
            dpi=150
        )
        assert page.image_data is None

    def test_invalid_page_number_zero(self):
        """测试页码为0时抛出异常。"""
        with pytest.raises(ValueError):
            PageImage(page_number=0, width=800, height=600, dpi=150)

    def test_invalid_page_number_negative(self):
        """测试负页码抛出异常。"""
        with pytest.raises(ValueError):
            PageImage(page_number=-1, width=800, height=600, dpi=150)

    def test_invalid_width_zero(self):
        """测试宽度为0时抛出异常。"""
        with pytest.raises(ValueError):
            PageImage(page_number=1, width=0, height=600, dpi=150)

    def test_invalid_width_negative(self):
        """测试负宽度抛出异常。"""
        with pytest.raises(ValueError):
            PageImage(page_number=1, width=-100, height=600, dpi=150)

    def test_invalid_height_zero(self):
        """测试高度为0时抛出异常。"""
        with pytest.raises(ValueError):
            PageImage(page_number=1, width=800, height=0, dpi=150)

    def test_invalid_dpi_zero(self):
        """测试DPI为0时抛出异常。"""
        with pytest.raises(ValueError):
            PageImage(page_number=1, width=800, height=600, dpi=0)


class TestTicketBoundingBox:
    """TicketBoundingBox模型测试类。"""

    def test_create_valid_bounding_box_ocr(self):
        """测试创建有效的OCR策略边界框。"""
        bbox = TicketBoundingBox(
            x1=100.0,
            y1=200.0,
            x2=500.0,
            y2=600.0,
            confidence=0.95,
            source_strategy="ocr",
            page_number=1
        )
        assert bbox.x1 == 100.0
        assert bbox.y1 == 200.0
        assert bbox.x2 == 500.0
        assert bbox.y2 == 600.0
        assert bbox.confidence == 0.95
        assert bbox.source_strategy == "ocr"
        assert bbox.page_number == 1

    def test_create_valid_bounding_box_contour(self):
        """测试创建有效的轮廓检测策略边界框。"""
        bbox = TicketBoundingBox(
            x1=50.0,
            y1=100.0,
            x2=300.0,
            y2=400.0,
            confidence=0.88,
            source_strategy="contour",
            page_number=2
        )
        assert bbox.source_strategy == "contour"

    def test_invalid_x2_less_than_x1(self):
        """测试x2小于等于x1时抛出异常。"""
        with pytest.raises(ValueError, match="x2必须大于x1"):
            TicketBoundingBox(
                x1=500.0,
                y1=200.0,
                x2=100.0,
                y2=600.0,
                confidence=0.9,
                source_strategy="ocr",
                page_number=1
            )

    def test_invalid_x2_equal_to_x1(self):
        """测试x2等于x1时抛出异常。"""
        with pytest.raises(ValueError, match="x2必须大于x1"):
            TicketBoundingBox(
                x1=100.0,
                y1=200.0,
                x2=100.0,
                y2=600.0,
                confidence=0.9,
                source_strategy="ocr",
                page_number=1
            )

    def test_invalid_y2_less_than_y1(self):
        """测试y2小于等于y1时抛出异常。"""
        with pytest.raises(ValueError, match="y2必须大于y1"):
            TicketBoundingBox(
                x1=100.0,
                y1=600.0,
                x2=500.0,
                y2=200.0,
                confidence=0.9,
                source_strategy="ocr",
                page_number=1
            )

    def test_invalid_confidence_negative(self):
        """测试负置信度抛出异常。"""
        with pytest.raises(ValueError):
            TicketBoundingBox(
                x1=100.0,
                y1=200.0,
                x2=500.0,
                y2=600.0,
                confidence=-0.1,
                source_strategy="ocr",
                page_number=1
            )

    def test_invalid_confidence_greater_than_one(self):
        """测试置信度大于1时抛出异常。"""
        with pytest.raises(ValueError):
            TicketBoundingBox(
                x1=100.0,
                y1=200.0,
                x2=500.0,
                y2=600.0,
                confidence=1.5,
                source_strategy="ocr",
                page_number=1
            )

    def test_invalid_source_strategy(self):
        """测试非法检测策略抛出异常。"""
        with pytest.raises(ValueError):
            TicketBoundingBox(
                x1=100.0,
                y1=200.0,
                x2=500.0,
                y2=600.0,
                confidence=0.9,
                source_strategy="invalid",
                page_number=1
            )

    def test_get_area(self):
        """测试计算边界框面积。"""
        bbox = TicketBoundingBox(
            x1=100.0,
            y1=200.0,
            x2=500.0,
            y2=600.0,
            confidence=0.9,
            source_strategy="ocr",
            page_number=1
        )
        area = bbox.get_area()
        assert area == 400.0 * 400.0
        assert area == 160000.0

    def test_get_dimensions(self):
        """测试获取边界框尺寸。"""
        bbox = TicketBoundingBox(
            x1=100.0,
            y1=200.0,
            x2=500.0,
            y2=600.0,
            confidence=0.9,
            source_strategy="ocr",
            page_number=1
        )
        width, height = bbox.get_dimensions()
        assert width == 400.0
        assert height == 400.0

    def test_boundary_edge_cases(self):
        """测试边界框的边缘情况。"""
        bbox = TicketBoundingBox(
            x1=0.0,
            y1=0.0,
            x2=1.0,
            y2=1.0,
            confidence=0.0,
            source_strategy="ocr",
            page_number=1
        )
        assert bbox.get_area() == 1.0


class TestTicketSplitResult:
    """TicketSplitResult模型测试类。"""

    def test_create_valid_split_result(self):
        """测试创建有效的拆分结果。"""
        result = TicketSplitResult(
            output_path="/path/to/ticket_0.png",
            ticket_index=0,
            source_page=1,
            width=800,
            height=600
        )
        assert result.output_path == "/path/to/ticket_0.png"
        assert result.ticket_index == 0
        assert result.source_page == 1
        assert result.width == 800
        assert result.height == 600
        assert result.bounding_box is None

    def test_split_result_with_bounding_box(self):
        """测试带边界框信息的拆分结果。"""
        bbox = TicketBoundingBox(
            x1=100.0,
            y1=200.0,
            x2=500.0,
            y2=600.0,
            confidence=0.95,
            source_strategy="ocr",
            page_number=1
        )
        result = TicketSplitResult(
            output_path="/path/to/ticket_0.png",
            ticket_index=0,
            source_page=1,
            bounding_box=bbox,
            width=400,
            height=400
        )
        assert result.bounding_box is not None
        assert result.bounding_box.confidence == 0.95

    def test_invalid_empty_output_path(self):
        """测试空输出路径抛出异常。"""
        with pytest.raises(ValueError, match="不能为空"):
            TicketSplitResult(
                output_path="",
                ticket_index=0,
                source_page=1,
                width=800,
                height=600
            )

    def test_invalid_whitespace_output_path(self):
        """测试纯空白输出路径抛出异常。"""
        with pytest.raises(ValueError, match="不能为空"):
            TicketSplitResult(
                output_path="   ",
                ticket_index=0,
                source_page=1,
                width=800,
                height=600
            )

    def test_output_path_trimmed(self):
        """测试输出路径自动去除首尾空白。"""
        result = TicketSplitResult(
            output_path="  /path/to/ticket.png  ",
            ticket_index=0,
            source_page=1,
            width=800,
            height=600
        )
        assert result.output_path == "/path/to/ticket.png"

    def test_invalid_negative_ticket_index(self):
        """测试负票据索引抛出异常。"""
        with pytest.raises(ValueError):
            TicketSplitResult(
                output_path="/path/to/ticket.png",
                ticket_index=-1,
                source_page=1,
                width=800,
                height=600
            )

    def test_valid_zero_ticket_index(self):
        """测试票据索引为0有效。"""
        result = TicketSplitResult(
            output_path="/path/to/ticket.png",
            ticket_index=0,
            source_page=1,
            width=800,
            height=600
        )
        assert result.ticket_index == 0

    def test_invalid_source_page_zero(self):
        """测试来源页码为0时抛出异常。"""
        with pytest.raises(ValueError):
            TicketSplitResult(
                output_path="/path/to/ticket.png",
                ticket_index=0,
                source_page=0,
                width=800,
                height=600
            )

    def test_invalid_width_zero(self):
        """测试宽度为0时抛出异常。"""
        with pytest.raises(ValueError):
            TicketSplitResult(
                output_path="/path/to/ticket.png",
                ticket_index=0,
                source_page=1,
                width=0,
                height=600
            )

    def test_invalid_height_zero(self):
        """测试高度为0时抛出异常。"""
        with pytest.raises(ValueError):
            TicketSplitResult(
                output_path="/path/to/ticket.png",
                ticket_index=0,
                source_page=1,
                width=800,
                height=0
            )


class TestModelIntegration:
    """模型集成测试类。"""

    def test_full_workflow_models(self):
        """测试完整工作流中的模型组合。"""
        page = PageImage(
            page_number=1,
            width=1920,
            height=1080,
            dpi=220
        )

        bbox = TicketBoundingBox(
            x1=100.0,
            y1=200.0,
            x2=500.0,
            y2=600.0,
            confidence=0.92,
            source_strategy="ocr",
            page_number=page.page_number
        )

        width, height = bbox.get_dimensions()
        result = TicketSplitResult(
            output_path=f"/output/ticket_page{page.page_number}_0.png",
            ticket_index=0,
            source_page=page.page_number,
            bounding_box=bbox,
            width=int(width),
            height=int(height)
        )

        assert result.source_page == page.page_number
        assert result.bounding_box.source_strategy == "ocr"
        assert result.width == 400
        assert result.height == 400

    def test_multiple_tickets_from_same_page(self):
        """测试从同一页面提取多个票据。"""
        page = PageImage(page_number=1, width=2000, height=3000, dpi=300)

        bbox1 = TicketBoundingBox(
            x1=100, y1=100, x2=900, y2=800,
            confidence=0.95, source_strategy="ocr", page_number=1
        )
        bbox2 = TicketBoundingBox(
            x1=100, y1=1000, x2=900, y2=1700,
            confidence=0.90, source_strategy="contour", page_number=1
        )

        result1 = TicketSplitResult(
            output_path="/output/ticket_0.png",
            ticket_index=0,
            source_page=page.page_number,
            bounding_box=bbox1,
            width=800,
            height=700
        )
        result2 = TicketSplitResult(
            output_path="/output/ticket_1.png",
            ticket_index=1,
            source_page=page.page_number,
            bounding_box=bbox2,
            width=800,
            height=700
        )

        assert result1.ticket_index == 0
        assert result2.ticket_index == 1
        assert result1.source_page == result2.source_page
        assert result1.bounding_box.source_strategy == "ocr"
        assert result2.bounding_box.source_strategy == "contour"
