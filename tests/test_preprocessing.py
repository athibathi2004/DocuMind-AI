import pytest
import numpy as np
from PIL import Image
from app.preprocessing.image_processor import ImageProcessor, PreprocessingConfig
from app.preprocessing.pdf_renderer import default_pdf_renderer


def test_image_processor_basic():
    processor = ImageProcessor()
    # Create simple synthetic test image
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    # Add dummy text-like strokes
    img[100:120, 100:400] = 0

    processed, diag = processor.process(img)
    assert processed is not None
    assert "grayscale" in diag["steps_applied"]
    assert "clahe_contrast" in diag["steps_applied"]
    assert len(processed.shape) == 2  # Grayscale single-channel


def test_image_processor_resize():
    config = PreprocessingConfig(resize_target_width=500)
    processor = ImageProcessor(config=config)
    img = np.ones((800, 1000, 3), dtype=np.uint8) * 255
    processed, diag = processor.process(img)
    assert processed.shape[1] == 500
    assert any("resize(500)" in s for s in diag["steps_applied"])


def test_image_processor_deskew():
    processor = ImageProcessor()
    gray = np.ones((300, 300), dtype=np.uint8) * 255
    # A flat horizontal block should have minimal or zero skew
    gray[140:160, 50:250] = 0
    angle = processor.estimate_skew_angle(gray)
    assert abs(angle) < 5.0  # minimal skew


def test_pdf_renderer_render(sample_data_dir, tmp_path):
    pdf_path = sample_data_dir / "sample_invoice.pdf"
    if not pdf_path.exists():
        pytest.skip("sample_invoice.pdf not generated yet")

    pages = default_pdf_renderer.render_pages_to_images(pdf_path, tmp_path)
    assert len(pages) >= 1
    page_num, img_path, w, h = pages[0]
    assert page_num == 1
    assert img_path.exists()
    assert w > 0 and h > 0


def test_pdf_renderer_embedded_text(sample_data_dir):
    pdf_path = sample_data_dir / "sample_contract.pdf"
    if not pdf_path.exists():
        pytest.skip("sample_contract.pdf not generated yet")

    extracted = default_pdf_renderer.extract_embedded_text(pdf_path)
    assert len(extracted) >= 1
    assert "MASTER SERVICES AGREEMENT" in extracted[0]["full_text"]

