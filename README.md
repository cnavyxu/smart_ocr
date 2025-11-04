# smart_ocr

High-concurrency OCR parsing service powered by PaddleOCR, supporting 100k concurrent requests.

[中文文档](README_CN.md)

## Features

- ✨ Support for 100k concurrent requests
- 🚀 Load balancing across three NVIDIA 3090 GPUs
- 🔄 High-precision text recognition using PaddleOCR
- ⚡ High-performance async API built with FastAPI
- 🐳 Docker deployment support
- 📊 Support for both image URL and Base64 input

## Tech Stack

- Python 3.10+
- FastAPI - Async web framework
- PaddleOCR - OCR recognition engine
- CUDA 11.8 - GPU acceleration
- Pydantic - Data validation

## System Requirements

- OS: Ubuntu 22.04 or higher
- GPU: 3x NVIDIA 3090 (or other CUDA-capable GPUs)
- CUDA: 11.8+
- Docker (optional): 20.10+ with nvidia-docker2

## Server Configuration

- Three 3090 GPUs for parallel OCR processing
- PaddleOCR model for Chinese and English text recognition
- Python-based tech stack for high performance

## Quick Start

### Using Docker (Recommended)

1. Build the image:
```bash
docker-compose build
```

2. Start the service:
```bash
docker-compose up -d
```

3. View logs:
```bash
docker-compose logs -f
```

### Local Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the service:
```bash
python main.py
```

The service will start at `http://0.0.0.0:8000`.

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "gpu_count": 3
}
```

### OCR Recognition (Image URL)

```bash
curl -X POST "http://localhost:8000/v1/ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg"
  }'
```

### OCR Recognition (Base64)

```bash
curl -X POST "http://localhost:8000/v1/ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA..."
  }'
```

### Response Format

```json
{
  "results": [
    {
      "text": "Recognized text",
      "confidence": 0.98,
      "position": {
        "top_left": [10, 20],
        "top_right": [100, 20],
        "bottom_right": [100, 50],
        "bottom_left": [10, 50]
      }
    }
  ],
  "text_count": 1,
  "processing_time": 0.123,
  "duration_ms": 145.67
}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| SMART_OCR_GPU_DEVICE_IDS | 0,1,2 | GPU device IDs |
| SMART_OCR_USE_GPU | true | Enable GPU acceleration |
| SMART_OCR_PADDLE_LANG | ch | OCR language (ch/en) |
| SMART_OCR_MAX_QUEUE_SIZE | 100000 | Maximum queue size |
| SMART_OCR_MAX_WORKERS | 32 | Maximum worker threads |
| SMART_OCR_FETCH_TIMEOUT_SECONDS | 10.0 | Image download timeout |
| SMART_OCR_REQUEST_TIMEOUT_SECONDS | 25.0 | Request processing timeout |

## Project Structure

```
smart_ocr/
├── src/
│   └── smart_ocr/
│       ├── __init__.py          # Package initialization
│       ├── app.py               # FastAPI application
│       ├── config.py            # Configuration management
│       ├── models.py            # Data models
│       ├── ocr_service.py       # OCR service wrapper
│       ├── gpu_manager.py       # GPU load balancing
│       ├── orchestrator.py      # Request orchestrator
│       └── image_loader.py      # Image loading utilities
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker build file
├── docker-compose.yml           # Docker Compose config
├── test_client.py               # Test client script
└── README.md                    # English documentation
```

## Performance Optimizations

1. **GPU Load Balancing**: Round-robin algorithm distributes tasks across three GPUs
2. **Async Processing**: FastAPI and asyncio for high concurrency
3. **Request Throttling**: Semaphore controls maximum concurrency
4. **Connection Pooling**: httpx async HTTP client
5. **Lazy Initialization**: PaddleOCR models loaded on-demand

## Testing

Run the test client:
```bash
python test_client.py
```

This will test:
- Health check endpoint
- OCR with image URL
- Concurrent request handling

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!
