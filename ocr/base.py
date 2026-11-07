from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np


@dataclass
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    polygon: Optional[List[List[float]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "polygon": self.polygon,
        }

    @property
    def width(self) -> float:
        return max(0.0, self.x_max - self.x_min)

    @property
    def height(self) -> float:
        return max(0.0, self.y_max - self.y_min)

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class TextBlockData:
    text: str
    bbox: BoundingBox
    confidence: float
    page_number: int
    block_type: str = "LINE"
    reading_order: int = 0
    line_number: int = 0


@dataclass
class OCRPageData:
    page_number: int
    width: int
    height: int
    blocks: List[TextBlockData] = field(default_factory=list)
    raw_text: str = ""
    average_confidence: float = 0.0
    execution_time_ms: int = 0
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class BaseOCREngine(ABC):
    """Abstract interface for all OCR engine implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the OCR provider."""
        pass

    @abstractmethod
    def extract_page(
        self,
        image_input: Union[str, Path, np.ndarray],
        page_number: int = 1,
        doc_name_hint: Optional[str] = None,
    ) -> OCRPageData:
        """Process an image and extract text blocks with bounding boxes and confidences."""
        pass

    def extract_document(
        self,
        pages: List[Union[str, Path, np.ndarray]],
    ) -> List[OCRPageData]:
        """Process multiple document pages."""
        results = []
        for idx, page in enumerate(pages):
            results.append(self.extract_page(page, page_number=idx + 1))
        return results

    @abstractmethod
    def get_diagnostics(self) -> Dict[str, Any]:
        """Return engine status, loaded model information, and health telemetry."""
        pass

