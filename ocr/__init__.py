from typing import Optional
from app.config import settings
from app.ocr.base import BaseOCREngine, OCRPageData, TextBlockData, BoundingBox
from app.ocr.mock_engine import MockOCREngine, mock_ocr_engine


def get_ocr_engine(provider: Optional[str] = None) -> BaseOCREngine:
    """Factory to retrieve the configured OCR engine."""
    provider_name = (provider or settings.OCR_PROVIDER).lower()

    if provider_name == "paddle":
        from app.ocr.paddle_engine import PaddleOCREngine
        return PaddleOCREngine(lang=settings.OCR_LANG, use_gpu=settings.OCR_USE_GPU)
    # Default to deterministic mock engine for guaranteed offline reproducibility
    return mock_ocr_engine


__all__ = [
    "BaseOCREngine",
    "OCRPageData",
    "TextBlockData",
    "BoundingBox",
    "MockOCREngine",
    "mock_ocr_engine",
    "get_ocr_engine",
]
