"""简单票据拆分器实现。

提供基本的票据图像裁剪和保存功能，用于测试和演示。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .models import BoundingBox, TicketImage, TicketSplitResult


class SimpleTicketSplitter:
    """简单票据拆分器。
    
    根据边界框裁剪原始图像并保存为独立文件。
    文件命名格式: page_{page_number}_ticket_{index}.png
    """
    
    def __init__(self, image_format: str = "PNG"):
        """初始化拆分器。
        
        参数:
            image_format: 保存的图像格式，默认PNG
        """
        self.image_format = image_format.upper()
        if self.image_format not in ("PNG", "JPEG", "JPG"):
            raise ValueError(f"不支持的图像格式: {image_format}")
    
    def split(
        self,
        image: Image.Image,
        bounding_boxes: List[BoundingBox],
        page_number: int = 1,
        output_dir: Optional[Path] = None,
        save_to_disk: bool = True,
    ) -> TicketSplitResult:
        """根据边界框拆分票据图像。
        
        参数:
            image: 原始页面图像
            bounding_boxes: 票据边界框列表
            page_number: 页码
            output_dir: 输出目录，save_to_disk为True时必需
            save_to_disk: 是否保存到磁盘
        
        返回:
            票据拆分结果
        
        异常:
            ValueError: 参数验证失败
            IOError: 文件保存失败
        """
        if save_to_disk and output_dir is None:
            raise ValueError("save_to_disk为True时必须提供output_dir")
        
        start_time = time.time()
        tickets: List[TicketImage] = []
        
        for idx, bbox in enumerate(bounding_boxes):
            # 裁剪图像
            x1, y1, x2, y2 = bbox.to_coordinates()
            cropped = image.crop((x1, y1, x2, y2))
            
            # 准备票据对象
            saved_path = None
            
            if save_to_disk and output_dir:
                # 生成文件名
                ext = self.image_format.lower()
                if ext == "jpg":
                    ext = "jpeg"
                filename = f"page_{page_number}_ticket_{idx}.{ext}"
                saved_path = output_dir / filename
                
                # 保存到磁盘
                try:
                    cropped.save(saved_path, format=self.image_format)
                except Exception as e:
                    raise IOError(f"保存票据图像失败: {saved_path}, 原因: {e}") from e
            
            ticket = TicketImage(
                image=cropped,
                bbox=bbox,
                page_number=page_number,
                ticket_index=idx,
                saved_path=saved_path,
            )
            tickets.append(ticket)
        
        split_time = time.time() - start_time
        
        return TicketSplitResult(
            page_number=page_number,
            tickets=tickets,
            split_time=split_time,
        )
