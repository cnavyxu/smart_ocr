#!/usr/bin/env python3
"""
Example client for testing the Smart OCR service.
"""
import asyncio
import base64
from pathlib import Path

import httpx


async def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}\n")


async def test_ocr_from_url():
    """Test OCR with an image URL."""
    print("Testing OCR with image URL...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/ocr",
            json={
                "image_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"
            },
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Found {result['text_count']} text regions")
            print(f"Processing time: {result['processing_time']:.3f}s")
            print(f"Total duration: {result['duration_ms']:.2f}ms")
            for idx, text_result in enumerate(result["results"][:3], 1):
                print(f"  {idx}. {text_result['text']} (conf: {text_result['confidence']:.2f})")
        else:
            print(f"Error: {response.text}")
        print()


async def test_ocr_from_base64(image_path: str):
    """Test OCR with base64 encoded image."""
    print(f"Testing OCR with base64 image from {image_path}...")
    
    if not Path(image_path).exists():
        print(f"Image file not found: {image_path}")
        print("Skipping base64 test.\n")
        return
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/ocr",
            json={"image_base64": image_base64},
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Found {result['text_count']} text regions")
            print(f"Processing time: {result['processing_time']:.3f}s")
            for idx, text_result in enumerate(result["results"][:5], 1):
                print(f"  {idx}. {text_result['text']}")
        else:
            print(f"Error: {response.text}")
        print()


async def test_concurrent_requests(num_requests: int = 10):
    """Test concurrent OCR requests."""
    print(f"Testing {num_requests} concurrent requests...")
    
    async def single_request(request_id: int):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/v1/ocr",
                json={
                    "image_url": "https://images.unsplash.com/photo-1546410531-bb4caa6b424d"
                },
            )
            return request_id, response.status_code, response.json() if response.status_code == 200 else None
    
    tasks = [single_request(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if isinstance(r, tuple) and r[1] == 200)
    print(f"Completed: {success_count}/{num_requests} successful")
    
    if success_count > 0:
        avg_time = sum(r[2]["processing_time"] for r in results if isinstance(r, tuple) and r[1] == 200) / success_count
        print(f"Average processing time: {avg_time:.3f}s")
    print()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Smart OCR Service Test Client")
    print("=" * 60)
    print()
    
    await test_health_check()
    
    await test_ocr_from_url()
    
    await test_concurrent_requests(10)
    
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
