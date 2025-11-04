#!/usr/bin/env python3
"""Smart OCR服务的测试客户端。

该脚本提供了多种测试场景，用于验证OCR服务的功能和性能：
- 健康检查测试
- 图像URL识别测试
- 图像Base64识别测试
- PDF文件识别测试
- 并发压力测试
"""
import asyncio
import base64
from pathlib import Path

import httpx


async def test_health_check():
    """测试健康检查端点。

    验证服务是否正常运行并返回正确的状态信息。
    """
    print("测试健康检查...")
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}\n")


async def test_ocr_from_url():
    """测试通过图像URL进行OCR识别。

    使用公开的图像URL进行测试，验证服务的基本OCR功能。
    """
    print("测试基于URL的图像OCR...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/ocr",
            json={
                "image_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"
            },
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"识别到 {result['text_count']} 个文本区域")
            print(f"处理时间: {result['processing_time']:.3f}秒")
            print(f"总耗时: {result['duration_ms']:.2f}毫秒")
            for idx, text_result in enumerate(result["results"][:3], 1):
                print(
                    f"  {idx}. {text_result['text']} (置信度: {text_result['confidence']:.2f})"
                )
        else:
            print(f"错误: {response.text}")
        print()


async def test_ocr_from_base64(image_path: str):
    """测试通过Base64编码的图像进行OCR识别。

    参数:
        image_path: 本地图像文件的路径
    """
    print(f"测试基于Base64的图像OCR（文件: {image_path}）...")

    if not Path(image_path).exists():
        print(f"图像文件不存在: {image_path}")
        print("跳过Base64测试。\n")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/ocr",
            json={"image_base64": image_base64},
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"识别到 {result['text_count']} 个文本区域")
            print(f"处理时间: {result['processing_time']:.3f}秒")
            for idx, text_result in enumerate(result["results"][:5], 1):
                print(f"  {idx}. {text_result['text']}")
        else:
            print(f"错误: {response.text}")
        print()


async def test_ocr_from_pdf(pdf_path: str):
    """测试通过Base64编码的PDF文件进行OCR识别。

    参数:
        pdf_path: 本地PDF文件的路径
    """
    print(f"测试PDF文件OCR（文件: {pdf_path}）...")

    if not Path(pdf_path).exists():
        print(f"PDF文件不存在: {pdf_path}")
        print("跳过PDF测试。\n")
        return

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/ocr",
            json={"pdf_base64": pdf_base64},
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"总页数: {result.get('page_count', 'N/A')}")
            print(f"识别到 {result['text_count']} 个文本区域")
            print(f"处理时间: {result['processing_time']:.3f}秒")
            print(f"总耗时: {result['duration_ms']:.2f}毫秒")
            print("前5个文本区域:")
            for idx, text_result in enumerate(result["results"][:5], 1):
                page_info = f" [第{text_result.get('page', '?')}页]" if 'page' in text_result else ""
                print(f"  {idx}. {text_result['text']}{page_info}")
        else:
            print(f"错误: {response.text}")
        print()


async def test_concurrent_requests(num_requests: int = 10):
    """测试并发OCR请求处理能力。

    参数:
        num_requests: 要发送的并发请求数量
    """
    print(f"测试 {num_requests} 个并发请求...")

    async def single_request(request_id: int):
        """执行单个OCR请求。"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/v1/ocr",
                json={
                    "image_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"
                },
            )
            return (
                request_id,
                response.status_code,
                response.json() if response.status_code == 200 else None,
            )

    tasks = [single_request(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(
        1 for r in results if isinstance(r, tuple) and r[1] == 200
    )
    print(f"完成: {success_count}/{num_requests} 成功")

    if success_count > 0:
        avg_time = (
            sum(
                r[2]["processing_time"]
                for r in results
                if isinstance(r, tuple) and r[1] == 200
            )
            / success_count
        )
        print(f"平均处理时间: {avg_time:.3f}秒")
    print()


async def main():
    """运行所有测试用例。"""
    print("=" * 60)
    print("Smart OCR 服务测试客户端")
    print("=" * 60)
    print()

    await test_health_check()

    await test_ocr_from_url()

    await test_concurrent_requests(10)

    print("所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
