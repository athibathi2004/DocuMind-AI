import pytest
from app.ocr.base import TextBlockData, BoundingBox
from app.layout.analyzer import LayoutAnalyzer
from app.layout.text_blocks import calculate_iou, is_vertically_aligned


def test_calculate_iou():
    box1 = BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10)
    box2 = BoundingBox(x_min=5, y_min=0, x_max=15, y_max=10)
    # intersection: 5 * 10 = 50, union: 100 + 100 - 50 = 150 -> 50/150 = 0.333
    iou = calculate_iou(box1, box2)
    assert 0.32 < iou < 0.34

    box3 = BoundingBox(x_min=20, y_min=20, x_max=30, y_max=30)
    assert calculate_iou(box1, box3) == 0.0


def test_is_vertically_aligned():
    b1 = BoundingBox(x_min=50, y_min=10, x_max=200, y_max=30)
    b2 = BoundingBox(x_min=52, y_min=35, x_max=220, y_max=55)
    assert is_vertically_aligned(b1, b2, max_x_diff=10.0) is True

    b3 = BoundingBox(x_min=100, y_min=35, x_max=220, y_max=55)
    assert is_vertically_aligned(b1, b3, max_x_diff=10.0) is False


def test_layout_analyzer_headings_and_keyvalues():
    analyzer = LayoutAnalyzer()

    blocks = [
        TextBlockData("TAX INVOICE", BoundingBox(50, 20, 250, 60), 0.98, 1, "LINE", 1),
        TextBlockData("Invoice Number: INV-9901", BoundingBox(50, 80, 280, 100), 0.95, 1, "LINE", 2),
        TextBlockData("Invoice Date: 2026-04-01", BoundingBox(50, 105, 270, 125), 0.94, 1, "LINE", 3),
        TextBlockData("Item | Qty | Rate | Total", BoundingBox(50, 160, 500, 185), 0.90, 1, "LINE", 4),
        TextBlockData("Consulting | 1 | $500 | $500", BoundingBox(50, 190, 500, 215), 0.90, 1, "LINE", 5),
    ]

    layout = analyzer.analyze(blocks)
    assert len(layout.ordered_blocks) == 5
    assert any(h.text == "TAX INVOICE" for h in layout.headings)
    assert any(kv.key == "Invoice Number" and kv.value == "INV-9901" for kv in layout.key_values)
    assert len(layout.tables) >= 1
    assert layout.tables[0].headers == ["Item", "Qty", "Rate", "Total"]

