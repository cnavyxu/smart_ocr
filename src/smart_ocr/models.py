from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, validator


class OCRRequest(BaseModel):
    """Request model for OCR endpoint."""

    image_url: Optional[str] = Field(
        default=None, description="URL of the image to process"
    )
    image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded image data"
    )

    @validator("image_base64", "image_url", pre=True, always=True)
    def validate_inputs(cls, v, values, **kwargs):
        field = kwargs.get("field")
        if field and field.name == "image_url":
            base64_value = values.get("image_base64")
            if not v and not base64_value:
                raise ValueError("Either image_url or image_base64 must be provided")
        return v


class TextPosition(BaseModel):
    """Position coordinates of detected text."""

    top_left: List[float]
    top_right: List[float]
    bottom_right: List[float]
    bottom_left: List[float]


class OCRTextResult(BaseModel):
    """Result for a single detected text region."""

    text: str = Field(description="Recognized text content")
    confidence: float = Field(description="Recognition confidence score")
    position: TextPosition = Field(description="Text bounding box coordinates")


class OCRResponse(BaseModel):
    """Response model for OCR endpoint."""

    results: List[OCRTextResult] = Field(
        description="List of recognized text regions"
    )
    text_count: int = Field(description="Number of text regions found")
    processing_time: float = Field(description="Processing time in seconds")
    duration_ms: float = Field(description="Total request duration in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    gpu_count: int
