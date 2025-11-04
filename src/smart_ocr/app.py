from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from smart_ocr import __version__
from smart_ocr.config import get_settings
from smart_ocr.image_loader import ImageProcessingError
from smart_ocr.models import HealthResponse, OCRRequest, OCRResponse
from smart_ocr.orchestrator import OCROrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Smart OCR Service",
    description="High-concurrency OCR service powered by PaddleOCR",
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
    """Initialize services on application startup."""
    logger.info("Starting Smart OCR Service")
    await orchestrator.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    logger.info("Shutting down Smart OCR Service")
    await orchestrator.stop()


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with service information."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        gpu_count=len(settings.gpu_device_ids),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        gpu_count=len(settings.gpu_device_ids),
    )


@app.post(f"{settings.api_prefix}/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest):
    """
    Perform OCR on the provided image.

    Args:
        request: OCR request containing image URL or base64 data

    Returns:
        OCR results with detected text and confidence scores
    """
    try:
        result = await orchestrator.process_request(request)
        return result
    except ImageProcessingError as exc:
        logger.error(f"Image processing error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during OCR processing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OCR processing",
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
