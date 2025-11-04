from __future__ import annotations

"""负责加载和预处理待识别文件（图像或PDF）的工具函数。"""

import base64
from typing import List, Optional, Tuple

import fitz
import httpx


class ImageProcessingError(Exception):
    """图像或文档处理过程中的自定义异常类。"""


async def load_image_from_request(
    image_url: Optional[str],
    image_base64: Optional[str],
    pdf_url: Optional[str],
    pdf_base64: Optional[str],
    timeout: float,
    pdf_dpi: int = 220,
) -> Tuple[List[bytes], bool, int]:
    """从请求参数中加载图像或PDF文件，并返回图像列表。

    该函数支持从URL或Base64字符串加载图像或PDF，并将结果统一转换为
    图像字节数据列表，以便后续进行OCR处理。

    参数:
        image_url: 图像文件的URL地址
        image_base64: Base64编码的图像数据
        pdf_url: PDF文件的URL地址
        pdf_base64: Base64编码的PDF数据
        timeout: 下载远程资源时的超时时间（秒）
        pdf_dpi: 将PDF页面渲染为图像时使用的DPI分辨率

    返回:
        元组包含三个元素:
        - List[bytes]: 图像字节列表（对于单张图像只有一个元素，PDF会有多个）
        - bool: 是否为PDF文件
        - int: 总页数/图像数量

    异常:
        ImageProcessingError: 当文件加载或处理失败时抛出
    """
    if pdf_url or pdf_base64:
        pdf_data = await _load_pdf_data(pdf_url, pdf_base64, timeout)
        return _convert_pdf_to_images(pdf_data, pdf_dpi)

    if image_base64:
        try:
            image_bytes = base64.b64decode(image_base64)
            return [image_bytes], False, 1
        except Exception as exc:
            raise ImageProcessingError(
                f"解码Base64图像数据失败: {exc}"
            ) from exc

    if image_url:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return [response.content], False, 1
        except httpx.HTTPStatusError as exc:
            raise ImageProcessingError(
                f"下载图像失败 (HTTP {exc.response.status_code}): {exc}"
            ) from exc
        except Exception as exc:
            raise ImageProcessingError(f"从URL加载图像时出错: {exc}") from exc

    raise ImageProcessingError("必须提供至少一种有效的输入数据来源")


async def _load_pdf_data(
    pdf_url: Optional[str],
    pdf_base64: Optional[str],
    timeout: float,
) -> bytes:
    """加载PDF文件的二进制数据。

    参数:
        pdf_url: PDF文件的URL地址
        pdf_base64: Base64编码的PDF数据
        timeout: 下载超时时间（秒）

    返回:
        PDF文件的二进制字节数据

    异常:
        ImageProcessingError: 当PDF加载失败时抛出
    """
    if pdf_base64:
        try:
            return base64.b64decode(pdf_base64)
        except Exception as exc:
            raise ImageProcessingError(f"解码Base64 PDF数据失败: {exc}") from exc

    if pdf_url:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPStatusError as exc:
            raise ImageProcessingError(
                f"下载PDF失败 (HTTP {exc.response.status_code}): {exc}"
            ) from exc
        except Exception as exc:
            raise ImageProcessingError(f"从URL加载PDF时出错: {exc}") from exc

    raise ImageProcessingError("未提供有效的PDF数据来源")


def _convert_pdf_to_images(
    pdf_data: bytes,
    dpi: int = 220,
) -> Tuple[List[bytes], bool, int]:
    """将PDF文件的每一页转换为独立的PNG图像。

    使用PyMuPDF (fitz) 库将PDF页面渲染为高分辨率图像，以便进行OCR识别。

    参数:
        pdf_data: PDF文件的二进制数据
        dpi: 渲染分辨率（DPI），数值越高图像质量越好但处理时间越长

    返回:
        元组包含三个元素:
        - List[bytes]: 每页渲染后的PNG图像字节列表
        - bool: 固定返回True，表示这是PDF来源
        - int: PDF的页数

    异常:
        ImageProcessingError: 当PDF解析或渲染失败时抛出
    """
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        page_count = len(doc)
        if page_count == 0:
            raise ImageProcessingError("提供的PDF文件不包含任何页面")

        images = []

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(page_count):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix)

            img_data = pix.tobytes("png")
            images.append(img_data)

        doc.close()
        return images, True, page_count

    except Exception as exc:
        raise ImageProcessingError(f"PDF转换为图像失败: {exc}") from exc
