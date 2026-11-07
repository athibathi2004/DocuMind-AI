import pytest
import numpy as np
from app.ocr.base import BoundingBox, BaseOCREngine
from app.ocr.mock_engine import MockOCREngine, mock_ocr_engine
from app.ocr import get_ocr_engine


def test_bounding_box_geometry():
    bbox = BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=70.0)
    assert bbox.width == 100.0
    assert bbox.height == 50.0
    assert bbox.area == 5000.0
    d = bbox.to_dict()
    assert d["x_min"] == 10.0
    assert d["y_max"] == 70.0


def test_mock_ocr_engine_deterministic():
    engine = MockOCREngine()
    dummy_img = np.ones((500, 500, 3), dtype=np.uint8) * 255

    # Invoice template test
    page_data = engine.extract_page(dummy_img, page_number=1, doc_name_hint="sample_invoice.pdf")
    assert page_data.page_number == 1
    assert len(page_data.blocks) > 0
    assert page_data.average_confidence > 0.80
    assert any("INVOICE" in b.text for b in page_data.blocks)

    # Passport template test
    page_data_pass = engine.extract_page(dummy_img, page_number=1, doc_name_hint="sample_passport.png")
    assert any("PASSPORT" in b.text for b in page_data_pass.blocks)
    assert any("P<USA" in b.text for b in page_data_pass.blocks)


def test_ocr_factory():
    engine_mock = get_ocr_engine("mock")
    assert isinstance(engine_mock, MockOCREngine)
    assert engine_mock.name == "MockOCR"

    diag = engine_mock.get_diagnostics()
    assert diag["status"] == "ready"
    assert diag["offline_capable"] is True

