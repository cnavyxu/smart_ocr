"""PDF票据处理主控模块。

本模块提供PDFTicketProcessor类，协调PDF加载、票据检测与拆分的完整流程，
形成可独立集成的服务组件。
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional, Union

from PIL import Image

from ..config import Settings
from .exceptions import PDFTicketProcessingError
from .interfaces import PDFLoader, TicketDetector, TicketSplitter
from .models import TicketSplitResult
from .pdf_loader import PageImage, load_pdf_to_images

logger = logging.getLogger(__name__)


class DefaultPDFLoader:
    """默认PDF加载器实现，基于现有的pdf_loader模块。"""
    
    def __init__(self, dpi: int = 220):
        """初始化加载器。
        
        参数:
            dpi: 渲染DPI分辨率
        """
        self.dpi = dpi
    
    def load(
        self,
        pdf_source: Union[str, bytes, Path],
        dpi: Optional[int] = None,
    ) -> List[PageImage]:
        """加载PDF并转换为图像列表。
        
        参数:
            pdf_source: PDF数据源（文件路径或字节流）
            dpi: 渲染DPI分辨率，如果未指定则使用初始化时的值
        
        返回:
            PageImage对象列表
        
        异常:
            PDFLoadError: PDF加载失败
        """
        actual_dpi = dpi if dpi is not None else self.dpi
        return load_pdf_to_images(pdf_source, dpi=actual_dpi)


class CompositeDetector:
    """组合检测器，按顺序执行多个检测器并合并结果。
    
    支持配置多个检测器，按顺序对每页图像进行检测，
    并将所有检测到的边界框合并返回。
    """
    
    def __init__(self, detectors: List[TicketDetector]):
        """初始化组合检测器。
        
        参数:
            detectors: 检测器列表，按执行顺序排列
        """
        if not detectors:
            raise ValueError("检测器列表不能为空")
        self.detectors = detectors
    
    def detect(self, image: Image.Image, page_number: int = 1):
        """使用所有检测器依次检测并合并结果。
        
        参数:
            image: 待检测的PIL图像对象
            page_number: 页码
        
        返回:
            合并后的票据检测结果
        """
        from .models import BoundingBox, TicketDetectionResult
        
        all_boxes: List[BoundingBox] = []
        total_time = 0.0
        
        for detector in self.detectors:
            result = detector.detect(image, page_number)
            all_boxes.extend(result.bounding_boxes)
            if result.detection_time:
                total_time += result.detection_time
        
        return TicketDetectionResult(
            page_number=page_number,
            bounding_boxes=all_boxes,
            detection_time=total_time if total_time > 0 else None,
        )


class PDFTicketProcessor:
    """PDF票据处理器主控类。
    
    协调PDF加载、票据检测与拆分的完整流程，支持依赖注入和灵活配置。
    
    属性:
        settings: 应用配置对象
        pdf_loader: PDF加载器实例
        detector: 票据检测器实例（可以是组合检测器）
        splitter: 票据拆分器实例
        save_to_disk: 是否将拆分后的票据保存到磁盘
        debug_mode: 是否启用调试模式（输出中间结果）
    """
    
    def __init__(
        self,
        settings: Settings,
        detector: Optional[TicketDetector] = None,
        splitter: Optional[TicketSplitter] = None,
        pdf_loader: Optional[PDFLoader] = None,
        save_to_disk: bool = True,
        debug_mode: bool = False,
    ):
        """初始化票据处理器。
        
        参数:
            settings: 应用配置对象
            detector: 自定义检测器，如未提供需要在调用process_pdf时提供
            splitter: 自定义拆分器，如未提供需要在调用process_pdf时提供
            pdf_loader: 自定义PDF加载器，默认使用内置实现
            save_to_disk: 是否保存拆分结果到磁盘，默认True
            debug_mode: 是否启用调试模式，默认False
        """
        self.settings = settings
        self.detector = detector
        self.splitter = splitter
        self.pdf_loader = pdf_loader or DefaultPDFLoader(dpi=settings.pdf_render_dpi)
        self.save_to_disk = save_to_disk
        self.debug_mode = debug_mode
        
        logger.info(
            f"PDFTicketProcessor初始化完成: "
            f"save_to_disk={save_to_disk}, debug_mode={debug_mode}"
        )
    
    def process_pdf(
        self,
        pdf_source: Union[str, bytes, Path],
        output_dir: Optional[Path] = None,
        detector: Optional[TicketDetector] = None,
        splitter: Optional[TicketSplitter] = None,
    ) -> List[TicketSplitResult]:
        """处理PDF文件，完成加载、检测、拆分的完整流程。
        
        这是核心方法，按以下步骤执行：
        1. 使用pdf_loader加载PDF为页面图像列表
        2. 对每页图像调用检测器获取票据边界框
        3. 调用拆分器裁剪并保存票据图像
        4. 返回汇总的拆分结果列表
        
        参数:
            pdf_source: PDF数据源，可以是文件路径（str/Path）或字节流（bytes）
            output_dir: 输出目录路径，save_to_disk为True时必需
            detector: 临时使用的检测器，会覆盖初始化时的检测器
            splitter: 临时使用的拆分器，会覆盖初始化时的拆分器
        
        返回:
            TicketSplitResult列表，每个元素对应一页的拆分结果
        
        异常:
            PDFTicketProcessingError: 处理过程中的任何错误
            ValueError: 参数验证失败
        
        示例:
            >>> processor = PDFTicketProcessor(
            ...     settings=settings,
            ...     detector=my_detector,
            ...     splitter=my_splitter
            ... )
            >>> results = processor.process_pdf(
            ...     "document.pdf",
            ...     output_dir=Path("./output")
            ... )
            >>> print(f"共处理{len(results)}页，拆分出{sum(r.ticket_count for r in results)}张票据")
        """
        # 使用提供的或默认的检测器和拆分器
        active_detector = detector or self.detector
        active_splitter = splitter or self.splitter
        
        # 验证必需的组件
        if active_detector is None:
            raise ValueError("必须提供detector（检测器）")
        if active_splitter is None:
            raise ValueError("必须提供splitter（拆分器）")
        if self.save_to_disk and output_dir is None:
            raise ValueError("save_to_disk为True时必须提供output_dir")
        
        # 准备输出目录
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = time.time()
        
        # 阶段1: 加载PDF
        logger.info("开始加载PDF...")
        try:
            pages = self._load_pdf(pdf_source)
            logger.info(f"PDF加载完成，共{len(pages)}页")
        except Exception as e:
            raise PDFTicketProcessingError(
                f"PDF加载失败: {str(e)}",
                stage="loading",
                original_error=e,
            ) from e
        
        # 阶段2和3: 检测与拆分
        results: List[TicketSplitResult] = []
        total_tickets = 0
        
        for page in pages:
            # 检测票据（内部已处理异常）
            detection_result = self._detect_tickets(
                page.image, 
                page.page_number,
                active_detector,
            )
            logger.info(
                f"第{page.page_number}页检测到{detection_result.ticket_count}张票据"
            )
            
            # 拆分票据（内部已处理异常）
            split_result = self._split_tickets(
                page.image,
                detection_result.bounding_boxes,
                page.page_number,
                output_dir,
                active_splitter,
            )
            
            results.append(split_result)
            total_tickets += split_result.ticket_count
        
        elapsed_time = time.time() - start_time
        
        # 输出统计日志
        logger.info(
            f"PDF处理完成: 共{len(pages)}页，拆分出{total_tickets}张票据，"
            f"耗时{elapsed_time:.2f}秒"
        )
        
        if self.debug_mode:
            self._log_debug_statistics(results)
        
        return results
    
    def _load_pdf(
        self,
        pdf_source: Union[str, bytes, Path],
    ) -> List[PageImage]:
        """加载PDF文件。
        
        参数:
            pdf_source: PDF数据源
        
        返回:
            PageImage对象列表
        
        异常:
            Exception: 加载失败时抛出
        """
        return self.pdf_loader.load(pdf_source, dpi=self.settings.pdf_render_dpi)
    
    def _detect_tickets(
        self,
        image: Image.Image,
        page_number: int,
        detector: TicketDetector,
    ):
        """检测页面中的票据。
        
        参数:
            image: 页面图像
            page_number: 页码
            detector: 检测器实例
        
        返回:
            票据检测结果
        
        异常:
            Exception: 检测失败时抛出
        """
        try:
            return detector.detect(image, page_number)
        except Exception as e:
            raise PDFTicketProcessingError(
                f"票据检测失败: {str(e)}",
                stage="detection",
                original_error=e,
            ) from e
    
    def _split_tickets(
        self,
        image: Image.Image,
        bounding_boxes,
        page_number: int,
        output_dir: Optional[Path],
        splitter: TicketSplitter,
    ):
        """拆分并保存票据图像。
        
        参数:
            image: 页面图像
            bounding_boxes: 边界框列表
            page_number: 页码
            output_dir: 输出目录
            splitter: 拆分器实例
        
        返回:
            票据拆分结果
        
        异常:
            Exception: 拆分失败时抛出
        """
        try:
            return splitter.split(
                image=image,
                bounding_boxes=bounding_boxes,
                page_number=page_number,
                output_dir=output_dir,
                save_to_disk=self.save_to_disk,
            )
        except Exception as e:
            raise PDFTicketProcessingError(
                f"票据拆分失败: {str(e)}",
                stage="splitting",
                original_error=e,
            ) from e
    
    def _log_debug_statistics(self, results: List[TicketSplitResult]) -> None:
        """输出调试统计信息。
        
        参数:
            results: 拆分结果列表
        """
        logger.debug("=" * 60)
        logger.debug("详细统计信息:")
        logger.debug(f"总页数: {len(results)}")
        
        for result in results:
            logger.debug(
                f"  第{result.page_number}页: {result.ticket_count}张票据"
            )
            if result.split_time:
                logger.debug(f"    拆分耗时: {result.split_time:.3f}秒")
            
            for ticket in result.tickets:
                if ticket.saved_path:
                    logger.debug(f"    -> {ticket.saved_path}")
        
        logger.debug("=" * 60)
