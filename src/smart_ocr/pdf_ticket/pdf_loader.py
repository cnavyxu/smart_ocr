"""PDF解析与图像加载模块。

本模块提供将多页PDF文件转换为高质量图像的功能，用于后续的票据检测与拆分处理。
支持从文件路径或字节流加载PDF，使用PyMuPDF库将每页渲染为指定DPI的图像。
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF未安装，请运行: pip install pymupdf")


class PDFLoadError(Exception):
    """PDF加载和处理过程中的自定义异常类。
    
    用于统一封装PDF解析、渲染等环节的各类错误，便于上层调用者捕获和处理。
    """


@dataclass
class PageImage:
    """PDF单页渲染后的图像及其元信息。
    
    属性:
        page_number: 页码（从1开始）
        image: PIL图像对象
        image_bytes: 图像的二进制数据（PNG或JPEG格式）
        width: 图像宽度（像素）
        height: 图像高度（像素）
        dpi: 渲染时使用的DPI分辨率
        format: 图像输出格式（'PNG' 或 'JPEG'）
    """
    
    page_number: int
    image: Image.Image
    image_bytes: bytes
    width: int
    height: int
    dpi: int
    format: str


def load_pdf_to_images(
    pdf_source: Union[str, bytes, Path],
    dpi: Optional[int] = None,
    output_format: str = "PNG",
    save_to_disk: bool = False,
    save_dir: Optional[Union[str, Path]] = None,
) -> List[PageImage]:
    """将PDF转换为高质量图像列表（统一入口函数）。
    
    这是主要的API函数，支持从文件路径或字节流加载PDF，并将每页渲染为图像。
    
    参数:
        pdf_source: PDF数据源，可以是文件路径（str或Path）或字节流（bytes）
        dpi: 渲染分辨率（DPI），默认从配置读取（220）
        output_format: 输出图像格式，支持 'PNG' 或 'JPEG'，默认 'PNG'
        save_to_disk: 是否将渲染后的图像保存到磁盘（用于调试）
        save_dir: 保存目录路径，如果save_to_disk为True但未指定，则使用当前目录
    
    返回:
        PageImage对象列表，每个对象包含一页的图像及元信息
    
    异常:
        PDFLoadError: PDF加载、解析或渲染失败时抛出
        ValueError: 参数格式不正确时抛出
    
    示例:
        >>> # 从文件路径加载
        >>> pages = load_pdf_to_images("document.pdf", dpi=300)
        >>> print(f"共{len(pages)}页")
        
        >>> # 从字节流加载
        >>> with open("document.pdf", "rb") as f:
        ...     pdf_bytes = f.read()
        >>> pages = load_pdf_to_images(pdf_bytes)
        
        >>> # 保存渲染结果用于调试
        >>> pages = load_pdf_to_images("document.pdf", save_to_disk=True, save_dir="./output")
    """
    if isinstance(pdf_source, (str, Path)):
        return load_pdf_from_path(
            pdf_path=pdf_source,
            dpi=dpi,
            output_format=output_format,
            save_to_disk=save_to_disk,
            save_dir=save_dir,
        )
    elif isinstance(pdf_source, bytes):
        return load_pdf_from_bytes(
            pdf_bytes=pdf_source,
            dpi=dpi,
            output_format=output_format,
            save_to_disk=save_to_disk,
            save_dir=save_dir,
        )
    else:
        raise ValueError(
            f"不支持的pdf_source类型: {type(pdf_source)}，"
            f"期望 str、Path 或 bytes"
        )


def load_pdf_from_path(
    pdf_path: Union[str, Path],
    dpi: Optional[int] = None,
    output_format: str = "PNG",
    save_to_disk: bool = False,
    save_dir: Optional[Union[str, Path]] = None,
) -> List[PageImage]:
    """从文件路径加载PDF并转换为图像列表。
    
    参数:
        pdf_path: PDF文件路径
        dpi: 渲染分辨率（DPI），默认从配置读取（220）
        output_format: 输出图像格式，支持 'PNG' 或 'JPEG'，默认 'PNG'
        save_to_disk: 是否将渲染后的图像保存到磁盘（用于调试）
        save_dir: 保存目录路径，如果save_to_disk为True但未指定，则使用当前目录
    
    返回:
        PageImage对象列表
    
    异常:
        PDFLoadError: PDF文件不存在、无法读取或解析失败时抛出
    """
    path = Path(pdf_path)
    if not path.exists():
        raise PDFLoadError(f"PDF文件不存在: {pdf_path}")
    
    if not path.is_file():
        raise PDFLoadError(f"路径不是文件: {pdf_path}")
    
    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as exc:
        raise PDFLoadError(f"读取PDF文件失败: {exc}") from exc
    
    return load_pdf_from_bytes(
        pdf_bytes=pdf_bytes,
        dpi=dpi,
        output_format=output_format,
        save_to_disk=save_to_disk,
        save_dir=save_dir,
    )


def load_pdf_from_bytes(
    pdf_bytes: bytes,
    dpi: Optional[int] = None,
    output_format: str = "PNG",
    save_to_disk: bool = False,
    save_dir: Optional[Union[str, Path]] = None,
) -> List[PageImage]:
    """从字节流加载PDF并转换为图像列表。
    
    参数:
        pdf_bytes: PDF文件的二进制数据
        dpi: 渲染分辨率（DPI），默认从配置读取（220）
        output_format: 输出图像格式，支持 'PNG' 或 'JPEG'，默认 'PNG'
        save_to_disk: 是否将渲染后的图像保存到磁盘（用于调试）
        save_dir: 保存目录路径，如果save_to_disk为True但未指定，则使用当前目录
    
    返回:
        PageImage对象列表
    
    异常:
        PDFLoadError: PDF字节流为空、格式无效或渲染失败时抛出
    """
    if not pdf_bytes:
        raise PDFLoadError("PDF字节流为空")
    
    if dpi is None:
        from ..config import get_settings
        dpi = get_settings().pdf_render_dpi
    
    if output_format.upper() not in ("PNG", "JPEG", "JPG"):
        raise ValueError(f"不支持的输出格式: {output_format}，仅支持 PNG 或 JPEG")
    
    output_format = "JPEG" if output_format.upper() == "JPG" else output_format.upper()
    
    if save_to_disk:
        if save_dir is None:
            save_dir = Path.cwd()
        else:
            save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFLoadError(f"无法打开PDF文档，可能文件已损坏: {exc}") from exc
    
    try:
        page_count = len(doc)
        if page_count == 0:
            raise PDFLoadError("PDF文档不包含任何页面")
        
        pages: List[PageImage] = []
        
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        
        for page_idx in range(page_count):
            try:
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(matrix=matrix)
                
                img_bytes = pix.tobytes(output_format.lower())
                
                pil_image = Image.open(io.BytesIO(img_bytes))
                
                page_image = PageImage(
                    page_number=page_idx + 1,
                    image=pil_image,
                    image_bytes=img_bytes,
                    width=pil_image.width,
                    height=pil_image.height,
                    dpi=dpi,
                    format=output_format,
                )
                
                pages.append(page_image)
                
                if save_to_disk and save_dir:
                    save_path = save_dir / f"page_{page_idx + 1}.{output_format.lower()}"
                    try:
                        pil_image.save(save_path)
                    except Exception as save_exc:
                        raise PDFLoadError(
                            f"保存第{page_idx + 1}页图像失败: {save_exc}"
                        ) from save_exc
                
            except PDFLoadError:
                raise
            except Exception as exc:
                raise PDFLoadError(
                    f"渲染第{page_idx + 1}页失败: {exc}"
                ) from exc
        
        return pages
    
    finally:
        doc.close()
