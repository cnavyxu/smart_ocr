from __future__ import annotations

"""FastAPI应用的核心定义，包括所有HTTP端点和中间件配置。"""

import logging

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from smart_ocr import __version__
from smart_ocr.config import get_settings
from smart_ocr.image_loader import ImageProcessingError
from smart_ocr.models import (
    HealthResponse,
    OCRRequest,
    OCRResponse,
    TaskListResponse,
    TaskProgressResponse,
    TaskStatisticsResponse,
    TaskStatus,
)
from smart_ocr.orchestrator import OCROrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Smart OCR Service",
    description="高并发OCR识别服务，由PaddleOCR驱动，支持图像和PDF文件识别",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = OCROrchestrator(settings)


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化回调函数。

    在服务启动时执行必要的初始化操作，包括：
    - 初始化OCR编排器
    - 预加载模型到各个GPU设备
    """
    logger.info("正在启动 Smart OCR 服务")
    await orchestrator.start()
    logger.info("Smart OCR 服务启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理回调函数。

    在服务停止时释放所有占用的资源，包括：
    - 停止OCR编排器
    - 关闭GPU工作进程
    - 清理临时资源
    """
    logger.info("正在关闭 Smart OCR 服务")
    await orchestrator.stop()
    logger.info("Smart OCR 服务已关闭")


@app.get("/", response_model=HealthResponse)
async def root():
    """根路径端点，返回服务的基本信息。

    返回:
        包含服务状态、版本号和GPU数量的健康响应对象
    """
    return HealthResponse(
        status="healthy",
        version=__version__,
        gpu_count=len(settings.gpu_device_ids),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点，供监控系统调用以确认服务运行正常。

    返回:
        包含服务状态、版本号和GPU数量的健康响应对象
    """
    return HealthResponse(
        status="healthy",
        version=__version__,
        gpu_count=len(settings.gpu_device_ids),
    )


@app.post(f"{settings.api_prefix}/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest, track_progress: bool = True):
    """执行OCR识别任务的核心端点。

    该接口支持以下输入方式：
    1. 通过URL提供图像文件 (image_url)
    2. 通过Base64编码提供图像数据 (image_base64)
    3. 通过URL提供PDF文件 (pdf_url)
    4. 通过Base64编码提供PDF数据 (pdf_base64)

    对于PDF文件，系统会自动将每一页转换为图像并逐页进行OCR识别，
    最终返回所有页面的识别结果。

    参数:
        request: OCR请求对象，包含待识别的文件数据
        track_progress: 是否启用任务进度跟踪（默认为True）

    返回:
        OCR识别结果，包含所有检测到的文本、位置信息和性能指标

    异常:
        HTTPException(400): 当输入数据无效或文件处理失败时
        HTTPException(500): 当服务内部出现未预期的错误时
    """
    try:
        result = await orchestrator.process_request(request, track_progress=track_progress)
        return result
    except ImageProcessingError as exc:
        logger.error(f"文件处理错误: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("OCR处理过程中发生意外错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR处理过程中发生内部服务器错误",
        )


@app.get(f"{settings.api_prefix}/tasks/{{task_id}}", response_model=TaskProgressResponse)
async def get_task_progress(task_id: str):
    """查询指定任务的执行进度。

    参数:
        task_id: 任务唯一标识符

    返回:
        包含任务进度和状态的详细信息

    异常:
        HTTPException(404): 当指定的任务不存在时
    """
    task_info = await orchestrator.get_task_status(task_id)
    if task_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在",
        )
    return TaskProgressResponse(**task_info)


@app.get(f"{settings.api_prefix}/tasks", response_model=TaskListResponse)
async def list_tasks(
    status_filter: TaskStatus | None = Query(
        default=None, description="按状态过滤任务"
    ),
    limit: int = Query(default=100, ge=1, le=1000, description="返回的最大任务数量"),
):
    """获取任务列表。

    参数:
        status_filter: 可选的状态过滤条件
        limit: 返回的最大任务数量（1-1000）

    返回:
        任务信息列表
    """
    tasks_raw = await orchestrator.list_tasks(status_filter=status_filter, limit=limit)
    tasks = [TaskProgressResponse(**item) for item in tasks_raw]
    return TaskListResponse(tasks=tasks, count=len(tasks))


@app.get(f"{settings.api_prefix}/tasks/statistics", response_model=TaskStatisticsResponse)
async def get_task_statistics():
    """获取任务执行的统计信息。

    返回:
        包含各状态任务数量和成功率的统计数据
    """
    stats = await orchestrator.get_task_statistics()
    return TaskStatisticsResponse(**stats)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器，捕获所有未被明确处理的异常。

    参数:
        request: 触发异常的HTTP请求对象
        exc: 捕获到的异常实例

    返回:
        标准化的JSON错误响应
    """
    logger.exception("捕获到未处理的异常")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "内部服务器错误"},
    )
