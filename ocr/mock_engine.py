import time
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import numpy as np
from PIL import Image

from app.ocr.base import BaseOCREngine, OCRPageData, TextBlockData, BoundingBox


class MockOCREngine(BaseOCREngine):
    """
    Deterministic mock OCR provider for fast, reliable offline testing.
    Provides realistic bounding boxes, text content, and varied confidence scores.
    """

    @property
    def name(self) -> str:
        return "MockOCR"

    def _get_passport_blocks(self, page_num: int, width: int, height: int) -> List[TextBlockData]:
        # Realistic passport layout blocks
        items = [
            ("PASSPORT / PASSEPORT", 0.99, [100, 50, 400, 80], "HEADING"),
            ("UNITED STATES OF AMERICA", 0.98, [100, 90, 550, 120], "HEADING"),
            ("Type / Type: P", 0.95, [100, 140, 250, 165], "LINE"),
            ("Country Code: USA", 0.96, [280, 140, 450, 165], "LINE"),
            ("Passport No: A12345678", 0.94, [500, 140, 720, 165], "KEY_VALUE"),
            ("Surname: HENDRICKS", 0.96, [100, 180, 350, 205], "KEY_VALUE"),
            ("Given Names: ELEANOR JANE", 0.93, [100, 220, 420, 245], "KEY_VALUE"),
            ("Nationality: UNITED STATES OF AMERICA", 0.95, [100, 260, 500, 285], "KEY_VALUE"),
            ("Date of Birth: 14 APR 1988", 0.92, [100, 300, 380, 325], "KEY_VALUE"),
            ("Sex: F", 0.97, [400, 300, 480, 325], "KEY_VALUE"),
            ("Place of Birth: CALIFORNIA, U.S.A.", 0.89, [100, 340, 450, 365], "KEY_VALUE"),
            ("Date of Issue: 12 JUN 2021", 0.91, [100, 380, 360, 405], "KEY_VALUE"),
            ("Date of Expiration: 11 JUN 2031", 0.92, [100, 420, 400, 445], "KEY_VALUE"),
            ("Authority: UNITED STATES DEPARTMENT OF STATE", 0.88, [100, 460, 580, 485], "LINE"),
            # MRZ Lines (44 characters TD3 standard)
            ("P<USAHENDRICKS<<ELEANOR<JANE<<<<<<<<<<<<<<<<", 0.95, [60, 540, 820, 570], "LINE"),
            ("A123456787USA8804144F3106114<<<<<<<<<<<<<<06", 0.94, [60, 580, 820, 610], "LINE"),
        ]
        blocks = []
        for idx, (text, conf, coords, btype) in enumerate(items):
            bbox = BoundingBox(
                x_min=float(coords[0]),
                y_min=float(coords[1]),
                x_max=float(coords[2]),
                y_max=float(coords[3]),
                polygon=[
                    [coords[0], coords[1]],
                    [coords[2], coords[1]],
                    [coords[2], coords[3]],
                    [coords[0], coords[3]],
                ],
            )
            blocks.append(
                TextBlockData(
                    text=text,
                    bbox=bbox,
                    confidence=conf,
                    page_number=page_num,
                    block_type=btype,
                    reading_order=idx + 1,
                    line_number=idx + 1,
                )
            )
        return blocks

    def _get_invoice_blocks(self, page_num: int, width: int, height: int) -> List[TextBlockData]:
        # Realistic invoice layout blocks
        items = [
            ("INVOICE", 0.99, [50, 40, 220, 80], "HEADING"),
            ("Acme Industrial Technologies Ltd.", 0.97, [50, 90, 450, 120], "HEADING"),
            ("Invoice Number: INV-2026-0842", 0.95, [500, 90, 780, 115], "KEY_VALUE"),
            ("Invoice Date: 2026-03-15", 0.94, [500, 125, 740, 150], "KEY_VALUE"),
            ("Due Date: 2026-04-15", 0.92, [500, 155, 710, 180], "KEY_VALUE"),
            ("Billed To: Global Systems Corp", 0.93, [50, 160, 350, 185], "KEY_VALUE"),
            ("Customer Address: 450 Innovation Parkway, Suite 300", 0.89, [50, 190, 480, 215], "LINE"),
            ("Tax ID: US-94810294", 0.88, [50, 220, 280, 245], "KEY_VALUE"),
            # Line items header
            ("Description | Qty | Unit Price | Total", 0.91, [50, 280, 750, 305], "TABLE_REGION"),
            ("Cloud Enterprise Subscription | 1 | $1,250.00 | $1,250.00", 0.90, [50, 315, 750, 340], "TABLE_REGION"),
            ("Managed Security Operations | 1 | $750.00 | $750.00", 0.89, [50, 350, 750, 375], "TABLE_REGION"),
            # Totals
            ("Subtotal: $2,000.00", 0.94, [480, 420, 750, 445], "KEY_VALUE"),
            ("Tax: $180.00", 0.91, [480, 455, 750, 480], "KEY_VALUE"),
            ("Total Amount: $2,180.00", 0.96, [480, 495, 760, 525], "KEY_VALUE"),
            ("Currency: USD", 0.95, [480, 535, 650, 560], "KEY_VALUE"),
            ("Payment Terms: Net 30 days. Thank you for your business.", 0.85, [50, 600, 580, 625], "PARAGRAPH"),
        ]
        blocks = []
        for idx, (text, conf, coords, btype) in enumerate(items):
            bbox = BoundingBox(
                x_min=float(coords[0]),
                y_min=float(coords[1]),
                x_max=float(coords[2]),
                y_max=float(coords[3]),
                polygon=[
                    [coords[0], coords[1]],
                    [coords[2], coords[1]],
                    [coords[2], coords[3]],
                    [coords[0], coords[3]],
                ],
            )
            blocks.append(
                TextBlockData(
                    text=text,
                    bbox=bbox,
                    confidence=conf,
                    page_number=page_num,
                    block_type=btype,
                    reading_order=idx + 1,
                    line_number=idx + 1,
                )
            )
        return blocks

    def _get_contract_blocks(self, page_num: int, width: int, height: int) -> List[TextBlockData]:
        items = [
            ("MASTER SERVICES AGREEMENT", 0.99, [150, 60, 650, 100], "HEADING"),
            ("This Agreement is entered into on 2026-01-10.", 0.93, [80, 130, 600, 160], "PARAGRAPH"),
            ("Between: Apex Technologies Inc.", 0.95, [80, 180, 420, 210], "KEY_VALUE"),
            ("And: Horizon Logistics LLC", 0.94, [80, 220, 400, 250], "KEY_VALUE"),
            ("1. Scope of Work and Deliverables", 0.96, [80, 280, 450, 310], "HEADING"),
            ("The Consultant agrees to provide document processing architectures.", 0.91, [80, 320, 720, 350], "PARAGRAPH"),
            ("Effective Date: 2026-01-15", 0.92, [80, 380, 350, 410], "KEY_VALUE"),
            ("Signatures: Authorized Representative", 0.88, [80, 460, 480, 490], "LINE"),
        ]
        blocks = []
        for idx, (text, conf, coords, btype) in enumerate(items):
            bbox = BoundingBox(
                x_min=float(coords[0]),
                y_min=float(coords[1]),
                x_max=float(coords[2]),
                y_max=float(coords[3]),
                polygon=[
                    [coords[0], coords[1]],
                    [coords[2], coords[1]],
                    [coords[2], coords[3]],
                    [coords[0], coords[3]],
                ],
            )
            blocks.append(
                TextBlockData(
                    text=text,
                    bbox=bbox,
                    confidence=conf,
                    page_number=page_num,
                    block_type=btype,
                    reading_order=idx + 1,
                    line_number=idx + 1,
                )
            )
        return blocks

    def _get_general_blocks(self, page_num: int, width: int, height: int) -> List[TextBlockData]:
        items = [
            ("EXECUTIVE MEMORANDUM", 0.98, [100, 50, 500, 90], "HEADING"),
            ("Organization: Department of Architecture", 0.94, [100, 110, 520, 140], "KEY_VALUE"),
            ("Date: 2026-02-20", 0.95, [100, 150, 300, 180], "KEY_VALUE"),
            ("Subject: Modern Document Intelligence Pipeline", 0.93, [100, 190, 600, 220], "KEY_VALUE"),
            ("Key Information: Migration to layout-aware extraction completed successfully.", 0.90, [100, 240, 750, 280], "PARAGRAPH"),
            ("All validation checkpoints and human-in-the-loop review queues are operational.", 0.89, [100, 290, 760, 320], "PARAGRAPH"),
        ]
        blocks = []
        for idx, (text, conf, coords, btype) in enumerate(items):
            bbox = BoundingBox(
                x_min=float(coords[0]),
                y_min=float(coords[1]),
                x_max=float(coords[2]),
                y_max=float(coords[3]),
                polygon=[
                    [coords[0], coords[1]],
                    [coords[2], coords[1]],
                    [coords[2], coords[3]],
                    [coords[0], coords[3]],
                ],
            )
            blocks.append(
                TextBlockData(
                    text=text,
                    bbox=bbox,
                    confidence=conf,
                    page_number=page_num,
                    block_type=btype,
                    reading_order=idx + 1,
                    line_number=idx + 1,
                )
            )
        return blocks

    def extract_page(
        self,
        image_input: Union[str, Path, np.ndarray],
        page_number: int = 1,
        doc_name_hint: Optional[str] = None,
    ) -> OCRPageData:
        start_time = time.time()

        # Determine dimensions and hints from image or path
        name_hint = (doc_name_hint or "").lower()
        width, height = 800, 1000

        if isinstance(image_input, (str, Path)):
            path_obj = Path(image_input)
            if not name_hint:
                name_hint = path_obj.name.lower()
            try:
                with Image.open(str(path_obj)) as img:
                    width, height = img.size
            except Exception:
                pass
        elif isinstance(image_input, np.ndarray):
            height, width = image_input.shape[:2]

        # Template routing based on filename hint or default
        if "passport" in name_hint:
            blocks = self._get_passport_blocks(page_number, width, height)
        elif "invoice" in name_hint or "bill" in name_hint:
            blocks = self._get_invoice_blocks(page_number, width, height)
        elif "contract" in name_hint or "agreement" in name_hint:
            blocks = self._get_contract_blocks(page_number, width, height)
        else:
            blocks = self._get_general_blocks(page_number, width, height)

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
                "mode": "deterministic_mock",
                "detected_template": name_hint or "general",
                "total_blocks": len(blocks),
            },
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "ready",
            "offline_capable": True,
            "supports_bounding_box": True,
            "supports_confidence": True,
        }


mock_ocr_engine = MockOCREngine()

