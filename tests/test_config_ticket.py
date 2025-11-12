"""票据配置项的单元测试。

测试票据检测与拆分相关配置项的解析、验证和默认值。
"""

import os
import tempfile
from typing import Any, Dict

import pytest

from smart_ocr.config import Settings


class TestTicketDetectionConfig:
    """票据检测配置测试类。"""

    def test_default_detection_strategies(self):
        """测试检测策略的默认值。"""
        settings = Settings()
        assert settings.ticket_detection_strategies == ["ocr", "contour"]

    def test_default_allow_ocr_detection(self):
        """测试OCR检测开关的默认值。"""
        settings = Settings()
        assert settings.ticket_allow_ocr_detection is True

    def test_default_allow_contour_detection(self):
        """测试轮廓检测开关的默认值。"""
        settings = Settings()
        assert settings.ticket_allow_contour_detection is True

    def test_default_detection_min_area(self):
        """测试最小面积阈值的默认值。"""
        settings = Settings()
        assert settings.ticket_detection_min_area == 10000

    def test_default_detection_min_text(self):
        """测试最小文本字符数的默认值。"""
        settings = Settings()
        assert settings.ticket_detection_min_text == 10

    def test_default_output_root(self):
        """测试输出根目录的默认值。"""
        settings = Settings()
        assert settings.ticket_output_root == "./outputs/tickets"
        assert os.path.exists(settings.ticket_output_root)

    def test_default_padding_pixels(self):
        """测试留白像素数的默认值。"""
        settings = Settings()
        assert settings.ticket_padding_pixels == 10


class TestDetectionStrategyValidation:
    """检测策略验证测试类。"""

    def test_parse_strategies_from_string(self, monkeypatch):
        """测试从环境变量字符串解析策略列表。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "ocr,contour")
        settings = Settings()
        assert settings.ticket_detection_strategies == ["ocr", "contour"]

    def test_parse_strategies_single_value(self, monkeypatch):
        """测试单个策略的解析。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "ocr")
        settings = Settings()
        assert settings.ticket_detection_strategies == ["ocr"]

    def test_parse_strategies_with_spaces(self, monkeypatch):
        """测试带空格的策略字符串解析。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", " ocr , contour ")
        settings = Settings()
        assert settings.ticket_detection_strategies == ["ocr", "contour"]

    def test_parse_strategies_case_insensitive(self, monkeypatch):
        """测试策略名称大小写不敏感。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "OCR,CONTOUR")
        settings = Settings()
        assert settings.ticket_detection_strategies == ["ocr", "contour"]

    def test_invalid_strategy_raises_error(self, monkeypatch):
        """测试非法策略名称抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "invalid_strategy")
        with pytest.raises(ValueError, match="Invalid detection strategy"):
            Settings()

    def test_empty_strategies_raises_error(self, monkeypatch):
        """测试空策略列表抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "")
        with pytest.raises(ValueError, match="At least one detection strategy"):
            Settings()

    def test_mixed_valid_invalid_strategies_raises_error(self, monkeypatch):
        """测试包含非法策略的混合列表抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "ocr,invalid")
        with pytest.raises(ValueError, match="Invalid detection strategy"):
            Settings()


class TestOutputRootValidation:
    """输出根目录验证测试类。"""

    def test_custom_output_root(self, monkeypatch):
        """测试自定义输出根目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "custom_tickets")
            monkeypatch.setenv("SMART_OCR_TICKET_OUTPUT_ROOT", custom_path)
            settings = Settings()
            assert settings.ticket_output_root == custom_path
            assert os.path.exists(custom_path)

    def test_output_root_auto_creation(self, monkeypatch):
        """测试输出目录不存在时自动创建。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = os.path.join(tmpdir, "auto_created", "tickets")
            monkeypatch.setenv("SMART_OCR_TICKET_OUTPUT_ROOT", new_path)
            settings = Settings()
            assert os.path.exists(new_path)

    def test_empty_output_root_raises_error(self, monkeypatch):
        """测试空输出根目录抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_OUTPUT_ROOT", "")
        with pytest.raises(ValueError, match="cannot be empty"):
            Settings()

    def test_whitespace_output_root_raises_error(self, monkeypatch):
        """测试纯空白字符的输出根目录抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_OUTPUT_ROOT", "   ")
        with pytest.raises(ValueError, match="cannot be empty"):
            Settings()


class TestThresholdValidation:
    """阈值参数验证测试类。"""

    def test_custom_min_area(self, monkeypatch):
        """测试自定义最小面积阈值。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_AREA", "20000")
        settings = Settings()
        assert settings.ticket_detection_min_area == 20000

    def test_zero_min_area_raises_error(self, monkeypatch):
        """测试零值最小面积抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_AREA", "0")
        with pytest.raises(ValueError, match="must be positive"):
            Settings()

    def test_negative_min_area_raises_error(self, monkeypatch):
        """测试负值最小面积抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_AREA", "-100")
        with pytest.raises(ValueError, match="must be positive"):
            Settings()

    def test_custom_min_text(self, monkeypatch):
        """测试自定义最小文本字符数。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_TEXT", "5")
        settings = Settings()
        assert settings.ticket_detection_min_text == 5

    def test_zero_min_text_valid(self, monkeypatch):
        """测试零值最小文本字符数有效。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_TEXT", "0")
        settings = Settings()
        assert settings.ticket_detection_min_text == 0

    def test_negative_min_text_raises_error(self, monkeypatch):
        """测试负值最小文本字符数抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_TEXT", "-1")
        with pytest.raises(ValueError, match="must be non-negative"):
            Settings()

    def test_custom_padding_pixels(self, monkeypatch):
        """测试自定义留白像素数。"""
        monkeypatch.setenv("SMART_OCR_TICKET_PADDING_PIXELS", "20")
        settings = Settings()
        assert settings.ticket_padding_pixels == 20

    def test_zero_padding_valid(self, monkeypatch):
        """测试零留白像素数有效。"""
        monkeypatch.setenv("SMART_OCR_TICKET_PADDING_PIXELS", "0")
        settings = Settings()
        assert settings.ticket_padding_pixels == 0

    def test_negative_padding_raises_error(self, monkeypatch):
        """测试负值留白像素数抛出异常。"""
        monkeypatch.setenv("SMART_OCR_TICKET_PADDING_PIXELS", "-5")
        with pytest.raises(ValueError, match="must be non-negative"):
            Settings()


class TestTicketDetectionSwitches:
    """票据检测开关测试类。"""

    def test_disable_ocr_detection(self, monkeypatch):
        """测试禁用OCR检测。"""
        monkeypatch.setenv("SMART_OCR_TICKET_ALLOW_OCR_DETECTION", "false")
        settings = Settings()
        assert settings.ticket_allow_ocr_detection is False

    def test_disable_contour_detection(self, monkeypatch):
        """测试禁用轮廓检测。"""
        monkeypatch.setenv("SMART_OCR_TICKET_ALLOW_CONTOUR_DETECTION", "false")
        settings = Settings()
        assert settings.ticket_allow_contour_detection is False

    def test_enable_switches_with_true(self, monkeypatch):
        """测试使用'true'字符串启用检测开关。"""
        monkeypatch.setenv("SMART_OCR_TICKET_ALLOW_OCR_DETECTION", "true")
        monkeypatch.setenv("SMART_OCR_TICKET_ALLOW_CONTOUR_DETECTION", "true")
        settings = Settings()
        assert settings.ticket_allow_ocr_detection is True
        assert settings.ticket_allow_contour_detection is True


class TestIntegrationScenarios:
    """集成场景测试类。"""

    def test_all_ticket_configs_together(self, monkeypatch):
        """测试所有票据配置项一起使用。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_output = os.path.join(tmpdir, "tickets_output")
            monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_STRATEGIES", "ocr")
            monkeypatch.setenv("SMART_OCR_TICKET_ALLOW_OCR_DETECTION", "true")
            monkeypatch.setenv("SMART_OCR_TICKET_ALLOW_CONTOUR_DETECTION", "false")
            monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_AREA", "15000")
            monkeypatch.setenv("SMART_OCR_TICKET_DETECTION_MIN_TEXT", "8")
            monkeypatch.setenv("SMART_OCR_TICKET_OUTPUT_ROOT", custom_output)
            monkeypatch.setenv("SMART_OCR_TICKET_PADDING_PIXELS", "15")

            settings = Settings()

            assert settings.ticket_detection_strategies == ["ocr"]
            assert settings.ticket_allow_ocr_detection is True
            assert settings.ticket_allow_contour_detection is False
            assert settings.ticket_detection_min_area == 15000
            assert settings.ticket_detection_min_text == 8
            assert settings.ticket_output_root == custom_output
            assert settings.ticket_padding_pixels == 15
            assert os.path.exists(custom_output)

    def test_settings_caching(self):
        """测试配置实例缓存。"""
        from smart_ocr.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
