"""票据分割器实现，根据边界框裁剪并保存票据图像。"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from PIL import Image

from smart_ocr.config import Settings
from smart_ocr.pdf_ticket.models import (
    PageImage,
    TicketBoundingBox,
    TicketSplitError,
    TicketSplitResult,
)

logger = logging.getLogger(__name__)


def generate_ticket_filename(
    page_number: int,
    ticket_index: int,
    format: str = "png",
) -> str:
    """生成票据文件名。
    
    按照规范格式生成文件名：page_{page_number}_ticket_{ticket_index}.{format}
    
    Args:
        page_number: 页码，从1开始
        ticket_index: 票据索引，从0开始
        format: 图像格式，默认为"png"
    
    Returns:
        生成的文件名字符串
    
    Examples:
        >>> generate_ticket_filename(1, 0)
        'page_1_ticket_0.png'
        >>> generate_ticket_filename(3, 5, "jpg")
        'page_3_ticket_5.jpg'
    """
    return f"page_{page_number}_ticket_{ticket_index}.{format}"


class TicketSplitter:
    """票据分割器，用于根据边界框裁剪并保存票据图像。
    
    该类提供了完整的票据分割流程：
    1. 根据边界框裁剪图像
    2. 应用可配置的padding
    3. 保存到规范的目录结构
    4. 支持可选的内存返回（BytesIO）
    
    Attributes:
        settings: 应用配置对象
        output_root: 输出文件的根目录
        image_format: 保存图像的格式（默认PNG）
        padding: 边界框周围的padding像素数
        save_to_disk: 是否保存文件到磁盘
        return_bytes: 是否在结果中返回图像字节数据
    """
    
    def __init__(
        self,
        settings: Settings,
        output_root: Path,
        image_format: str = "png",
        padding: int = 0,
        save_to_disk: bool = True,
        return_bytes: bool = False,
    ):
        """初始化票据分割器。
        
        Args:
            settings: 应用配置对象
            output_root: 输出文件的根目录路径
            image_format: 保存图像的格式，默认为"png"
            padding: 边界框周围的padding像素数，默认为0
            save_to_disk: 是否保存文件到磁盘，默认为True
            return_bytes: 是否在结果中返回图像字节数据，默认为False
        """
        self.settings = settings
        self.output_root = Path(output_root)
        self.image_format = image_format.lower()
        self.padding = padding
        self.save_to_disk = save_to_disk
        self.return_bytes = return_bytes
        
        logger.info(
            f"初始化TicketSplitter: output_root={self.output_root}, "
            f"format={self.image_format}, padding={self.padding}, "
            f"save_to_disk={self.save_to_disk}, return_bytes={self.return_bytes}"
        )
    
    def _ensure_output_directory(self, pdf_name: str) -> Path:
        """确保输出目录存在。
        
        创建目录结构：output_root/<pdf_name>/
        
        Args:
            pdf_name: PDF文件名（不含扩展名）
        
        Returns:
            输出目录的Path对象
        
        Raises:
            TicketSplitError: 如果目录创建失败
        """
        output_dir = self.output_root / pdf_name
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"确保输出目录存在: {output_dir}")
            return output_dir
        except Exception as e:
            error_msg = f"创建输出目录失败: {output_dir}, 错误: {e}"
            logger.error(error_msg)
            raise TicketSplitError(error_msg) from e
    
    def _crop_ticket_image(
        self,
        page_image: PageImage,
        bounding_box: TicketBoundingBox,
    ) -> Image.Image:
        """根据边界框裁剪票据图像。
        
        如果配置了padding，会先扩展边界框（并处理越界情况），然后进行裁剪。
        
        Args:
            page_image: 页面图像对象
            bounding_box: 票据边界框
        
        Returns:
            裁剪后的PIL图像对象
        
        Raises:
            TicketSplitError: 如果裁剪失败
        """
        try:
            # 应用padding并处理越界
            if self.padding > 0:
                box = bounding_box.expand_with_padding(
                    self.padding,
                    page_image.width,
                    page_image.height,
                )
            else:
                box = bounding_box
            
            # 裁剪图像
            cropped = page_image.image.crop((box.x1, box.y1, box.x2, box.y2))
            
            logger.debug(
                f"裁剪票据图像: 原始尺寸=({page_image.width}, {page_image.height}), "
                f"边界框=({box.x1}, {box.y1}, {box.x2}, {box.y2}), "
                f"裁剪后尺寸={cropped.size}"
            )
            
            return cropped
        except Exception as e:
            error_msg = f"裁剪图像失败: {e}"
            logger.error(error_msg)
            raise TicketSplitError(error_msg) from e
    
    def _save_ticket_image(
        self,
        image: Image.Image,
        output_path: Path,
    ) -> None:
        """保存票据图像到磁盘。
        
        Args:
            image: PIL图像对象
            output_path: 输出文件路径
        
        Raises:
            TicketSplitError: 如果保存失败
        """
        try:
            image.save(output_path, format=self.image_format.upper())
            logger.info(f"保存票据图像: {output_path}")
        except Exception as e:
            error_msg = f"保存图像失败: {output_path}, 错误: {e}"
            logger.error(error_msg)
            raise TicketSplitError(error_msg) from e
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """将PIL图像转换为字节数据。
        
        Args:
            image: PIL图像对象
        
        Returns:
            图像的字节数据
        
        Raises:
            TicketSplitError: 如果转换失败
        """
        try:
            buffer = BytesIO()
            image.save(buffer, format=self.image_format.upper())
            return buffer.getvalue()
        except Exception as e:
            error_msg = f"将图像转换为字节失败: {e}"
            logger.error(error_msg)
            raise TicketSplitError(error_msg) from e
    
    def split_page_tickets(
        self,
        page: PageImage,
        boxes: List[TicketBoundingBox],
    ) -> List[TicketSplitResult]:
        """对页面中的所有票据进行分割和保存。
        
        该方法是票据分割的主要入口点，处理以下流程：
        1. 确保输出目录存在
        2. 遍历所有边界框
        3. 裁剪每个票据图像（应用padding）
        4. 保存到磁盘（如果启用）
        5. 生成字节数据（如果启用）
        6. 返回包含元数据的结果列表
        
        Args:
            page: 页面图像对象
            boxes: 票据边界框列表
        
        Returns:
            票据分割结果列表，每个结果包含文件路径、尺寸等元数据
        
        Raises:
            TicketSplitError: 如果分割过程中出现错误
        
        Examples:
            >>> splitter = TicketSplitter(settings, Path("/output"))
            >>> page = PageImage.from_image(image, 1, "invoice_001")
            >>> boxes = [TicketBoundingBox(10, 10, 100, 100)]
            >>> results = splitter.split_page_tickets(page, boxes)
            >>> print(results[0].file_path)
            /output/invoice_001/page_1_ticket_0.png
        """
        if not boxes:
            logger.warning(f"页面{page.page_number}没有检测到票据边界框")
            return []
        
        # 确保输出目录存在
        output_dir = None
        if self.save_to_disk:
            output_dir = self._ensure_output_directory(page.pdf_name)
        
        results: List[TicketSplitResult] = []
        
        logger.info(
            f"开始分割页面{page.page_number}的{len(boxes)}个票据 "
            f"(PDF: {page.pdf_name})"
        )
        
        for ticket_index, box in enumerate(boxes):
            try:
                # 裁剪票据图像
                cropped_image = self._crop_ticket_image(page, box)
                width, height = cropped_image.size
                
                # 生成文件路径
                file_path = None
                if self.save_to_disk and output_dir:
                    filename = generate_ticket_filename(
                        page.page_number,
                        ticket_index,
                        self.image_format,
                    )
                    file_path = output_dir / filename
                    
                    # 保存到磁盘
                    self._save_ticket_image(cropped_image, file_path)
                
                # 生成字节数据
                image_bytes = None
                if self.return_bytes:
                    image_bytes = self._image_to_bytes(cropped_image)
                
                # 创建结果对象
                result = TicketSplitResult(
                    file_path=file_path,
                    page_number=page.page_number,
                    ticket_index=ticket_index,
                    bounding_box=box,
                    strategy=box.strategy,
                    width=width,
                    height=height,
                    image_bytes=image_bytes,
                )
                
                results.append(result)
                
                logger.debug(
                    f"成功分割票据: page={page.page_number}, "
                    f"index={ticket_index}, size=({width}, {height}), "
                    f"strategy={box.strategy}"
                )
                
            except TicketSplitError:
                # 重新抛出已经包装的异常
                raise
            except Exception as e:
                error_msg = (
                    f"分割页面{page.page_number}的票据{ticket_index}失败: {e}"
                )
                logger.error(error_msg)
                raise TicketSplitError(error_msg) from e
        
        logger.info(
            f"完成页面{page.page_number}的票据分割，共{len(results)}个票据"
        )
        
        return results
