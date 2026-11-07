import time
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import numpy as np
from PIL import Image

from app.core.logging import logger
from app.ocr.base import BaseOCREngine, OCRPageData, TextBlockData, BoundingBox
from app.ocr.mock_engine import mock_ocr_engine


class PaddleOCREngine(BaseOCREngine):
    """
    PaddleOCR provider integration.
    Supports deep-learning text detection and recognition with graceful fallback.
    """

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr = None
        self._init_error: Optional[str] = None
        self._initialize()

    def _initialize(self):
        try:
            from paddleocr import PaddleOCR
            # Initialize with low verbosity
            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            self._init_error = str(e)
            logger.warning(f"PaddleOCR initialization failed: {e}. Falling back to MockOCREngine.")

    @property
    def name(self) -> str:
        return "PaddleOCR"

    def extract_page(
        self,
        image_input: Union[str, Path, np.ndarray],
        page_number: int = 1,
        doc_name_hint: Optional[str] = None,
    ) -> OCRPageData:
        start_time = time.time()

        if self._ocr is None:
            # Gracefully delegate to mock engine if PaddleOCR is not functional in current runtime
            result = mock_ocr_engine.extract_page(image_input, page_number, doc_name_hint)
            result.diagnostics["engine_fallback"] = "PaddleOCR unavailable; used MockOCREngine"
            result.diagnostics["init_error"] = self._init_error
            return result

        try:
            # Handle image input
            if isinstance(image_input, (str, Path)):
                img_path = str(image_input)
                with Image.open(img_path) as img:
                    width, height = img.size
                raw_ocr = self._ocr.ocr(img_path, cls=True)
            elif isinstance(image_input, np.ndarray):
                height, width = image_input.shape[:2]
                raw_ocr = self._ocr.ocr(image_input, cls=True)
            else:
                raise ValueError(f"Unsupported image input type: {type(image_input)}")

            blocks: List[TextBlockData] = []
            if raw_ocr and len(raw_ocr) > 0 and raw_ocr[0] is not None:
                lines = raw_ocr[0]
                for idx, line in enumerate(lines):
                    # Paddle format: [ [ [x1,y1], [x2,y2], [x3,y3], [x4,y4] ], (text, confidence) ]
                    polygon = line[0]
                    text, conf = line[1]

                    xs = [pt[0] for pt in polygon]
                    ys = [pt[1] for pt in polygon]

                    bbox = BoundingBox(
                        x_min=float(min(xs)),
                        y_min=float(min(ys)),
                        x_max=float(max(xs)),
                        y_max=float(max(ys)),
                        polygon=polygon,
                    )

                    blocks.append(
                        TextBlockData(
                            text=str(text).strip(),
                            bbox=bbox,
                            confidence=round(float(conf), 4),
                            page_number=page_number,
                            block_type="LINE",
                            reading_order=idx + 1,
                            line_number=idx + 1,
                        )
                    )

            raw_text = "\n".join(b.text for b in blocks)
            avg_conf = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0
            elapsed_ms = int((time.time() - start_time) * 1000)

            return OCRPageData(
                page_number=page_number,
                width=width,
                height=height,
                blocks=blocks,
                raw_text=raw_text,
                average_confidence=round(avg_conf, 4),
                execution_time_ms=elapsed_ms,
                diagnostics={
                    "engine": self.name,
                    "mode": "neural_ocr",
                    "total_blocks": len(blocks),
                },
            )
        except Exception as e:
            logger.error(f"PaddleOCR runtime error: {e}. Falling back to mock engine.")
            fallback = mock_ocr_engine.extract_page(image_input, page_number)
            fallback.diagnostics["runtime_error"] = str(e)
            return fallback

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "ready" if self._ocr is not None else "degraded",
            "initialized": self._ocr is not None,
            "error": self._init_error,
            "lang": self.lang,
            "use_gpu": self.use_gpu,
        }

