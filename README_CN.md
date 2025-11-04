# Smart OCR 服务

基于 PaddleOCR 的高并发 OCR 解析服务，支持 10 万并发请求。

## 功能特性

- ✨ 支持 10 万并发请求处理
- 🚀 利用三卡 3090 GPU 进行负载均衡
- 🔄 基于 PaddleOCR 的高精度文字识别
- ⚡ FastAPI 构建的异步高性能 API
- 🐳 Docker 部署支持
- 📊 支持图片 / PDF 的 URL 与 Base64 双模式输入
- 📈 提供任务进度跟踪与统计接口
- 🔬 附带 10 万并发压力测试脚本

## 技术栈

- Python 3.10+
- FastAPI - 异步 Web 框架
- PaddleOCR - OCR 识别引擎
- CUDA 11.8 - GPU 加速
- Pydantic - 数据验证

## 系统要求

- 操作系统: Ubuntu 22.04 或更高版本
- GPU: 3x NVIDIA 3090 (或其他支持 CUDA 的 GPU)
- CUDA: 11.8+
- Docker (可选): 20.10+ 并安装 nvidia-docker2

## 快速开始

### 使用 Docker (推荐)

1. 构建镜像:
```bash
docker-compose build
```

2. 启动服务:
```bash
docker-compose up -d
```

3. 查看日志:
```bash
docker-compose logs -f
```

### 本地安装

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 启动服务:
```bash
python main.py
```

服务将在 `http://0.0.0.0:8000` 启动。

## API 使用

### 健康检查

```bash
curl http://localhost:8000/health
```

响应:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "gpu_count": 3
}
```

### OCR 识别 (使用图片 URL，启用进度跟踪)

```bash
curl -X POST "http://localhost:8000/v1/ocr?track_progress=true" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg"
  }'
```

### OCR 识别 (使用 Base64 图像)

```bash
curl -X POST "http://localhost:8000/v1/ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA..."
  }'
```

### OCR 识别 (使用 PDF URL)

```bash
curl -X POST "http://localhost:8000/v1/ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://example.com/document.pdf"
  }'
```

### OCR 识别 (使用 Base64 PDF)

```bash
curl -X POST "http://localhost:8000/v1/ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_base64": "JVBERi0xLjQKJeLjz9MKMy..."
  }'
```

### 响应格式 (图像)

```json
{
  "results": [
    {
      "text": "识别到的文字",
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
  "duration_ms": 145.67,
  "page_count": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 响应格式 (PDF)

```json
{
  "results": [
    {
      "text": "第一页的文字",
      "confidence": 0.98,
      "position": {
        "top_left": [10, 20],
        "top_right": [100, 20],
        "bottom_right": [100, 50],
        "bottom_left": [10, 50]
      },
      "page": 1
    },
    {
      "text": "第二页的文字",
      "confidence": 0.95,
      "position": {
        "top_left": [15, 25],
        "top_right": [110, 25],
        "bottom_right": [110, 55],
        "bottom_left": [15, 55]
      },
      "page": 2
    }
  ],
  "text_count": 2,
  "processing_time": 0.456,
  "duration_ms": 523.45,
  "page_count": 2,
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 查询任务进度

```bash
curl "http://localhost:8000/v1/tasks/{task_id}"
```

### 获取任务列表

```bash
curl "http://localhost:8000/v1/tasks?limit=10"
```

### 获取任务统计信息

```bash
curl "http://localhost:8000/v1/tasks/statistics"
```

### 运行10万并发压力测试

```bash
python load_test_100k.py
```

## 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| SMART_OCR_GPU_DEVICE_IDS | 0,1,2 | GPU 设备 ID 列表 |
| SMART_OCR_USE_GPU | true | 是否使用 GPU |
| SMART_OCR_PADDLE_LANG | ch | OCR 语言 (ch/en) |
| SMART_OCR_MAX_QUEUE_SIZE | 100000 | 最大队列大小 |
| SMART_OCR_MAX_WORKERS | 32 | 最大工作线程数 |
| SMART_OCR_FETCH_TIMEOUT_SECONDS | 10.0 | 图片/PDF 下载超时 |
| SMART_OCR_REQUEST_TIMEOUT_SECONDS | 25.0 | 请求处理超时 |
| SMART_OCR_PDF_RENDER_DPI | 220 | PDF 渲染为图像时的DPI值 |

## 项目结构

```
smart_ocr/
├── src/
│   └── smart_ocr/
│       ├── __init__.py          # 包初始化
│       ├── app.py               # FastAPI 应用
│       ├── config.py            # 配置管理
│       ├── models.py            # 数据模型
│       ├── ocr_service.py       # OCR 服务封装
│       ├── gpu_manager.py       # GPU 负载均衡
│       ├── orchestrator.py      # 请求协调器
│       ├── task_tracker.py      # 任务进度跟踪
│       └── image_loader.py      # 图片/PDF 加载工具
├── main.py                      # 入口文件
├── test_progress.py             # 进度跟踪测试脚本
├── load_test_100k.py            # 10万并发负载测试脚本
├── requirements.txt             # Python 依赖
├── Dockerfile                   # Docker 构建文件
├── docker-compose.yml           # Docker Compose 配置
└── README_CN.md                 # 中文文档
```

## 性能优化

1. **GPU 负载均衡**: 采用 Round-Robin 算法在三块 GPU 间分配任务
2. **异步处理**: 使用 FastAPI 和 asyncio 实现高并发
3. **请求限流**: 通过 Semaphore 控制最大并发数
4. **连接池**: 使用 httpx 异步 HTTP 客户端
5. **惰性初始化**: PaddleOCR 模型按需加载

## 监控与日志

服务内置了详细的日志记录:
- 请求处理时间
- GPU 使用情况
- 错误追踪

查看日志:
```bash
# Docker 方式
docker-compose logs -f

# 本地方式
tail -f *.log
```

## 常见问题

### Q: 如何只使用部分 GPU?

A: 设置环境变量 `SMART_OCR_GPU_DEVICE_IDS=0,1` 只使用前两块 GPU。

### Q: 如何在没有 GPU 的环境中测试?

A: 设置 `SMART_OCR_USE_GPU=false`，服务将使用 CPU 模式。

### Q: 如何提高并发处理能力?

A: 调整 `SMART_OCR_MAX_QUEUE_SIZE` 和 `SMART_OCR_MAX_WORKERS` 参数。

### Q: PDF识别效果不理想怎么办?

A: 可以通过调整 `SMART_OCR_PDF_RENDER_DPI` 参数来提高PDF渲染质量（推荐范围：150-300），数值越高图像质量越好但处理时间越长。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
