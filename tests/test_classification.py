import pytest
from app.classification.classifier import DocumentClassifier
from app.models.document import DocumentCategory
from app.ocr.base import OCRPageData, TextBlockData, BoundingBox


def make_page(text_lines):
    blocks = [
        TextBlockData(line, BoundingBox(10, i * 20, 300, (i + 1) * 20), 0.95, 1, "LINE", i)
        for i, line in enumerate(text_lines)
    ]
    raw_text = "\n".join(text_lines)
    return OCRPageData(page_number=1, width=800, height=1000, blocks=blocks, raw_text=raw_text)


def test_classify_passport():
    classifier = DocumentClassifier()
    page = make_page([
        "PASSPORT",
        "UNITED STATES OF AMERICA",
        "P<USAHENDRICKS<<ELEANOR<JANE<<<<<<<<<<<<<<<<",
        "A123456787USA8804144F3106114<<<<<<<<<<<<<<06",
    ])
    cat, conf, expl, diag = classifier.classify([page])
    assert cat == DocumentCategory.PASSPORT
    assert conf >= 0.90
    assert "MRZ" in expl or "passport" in expl.lower()


def test_classify_invoice():
    classifier = DocumentClassifier()
    page = make_page([
        "COMMERCIAL INVOICE",
        "Invoice Number: INV-2026-0842",
        "Bill To: Global Systems Corp",
        "Subtotal: $2,000.00",
        "Tax: $180.00",
        "Total Amount: $2,180.00",
    ])
    cat, conf, expl, diag = classifier.classify([page])
    assert cat == DocumentCategory.INVOICE
    assert conf >= 0.80


def test_classify_contract():
    classifier = DocumentClassifier()
    page = make_page([
        "MASTER SERVICES AGREEMENT",
        "This Agreement is entered into by and between the parties.",
        "Terms and Conditions:",
        "Effective Date: 2026-01-15",
    ])
    cat, conf, expl, diag = classifier.classify([page])
    assert cat == DocumentCategory.CONTRACT
    assert conf >= 0.70


def test_classify_unknown():
    classifier = DocumentClassifier()
    page = make_page(["Just random gibberish", "Nothing recognizable here 12345"])
    cat, conf, expl, diag = classifier.classify([page])
    assert cat == DocumentCategory.UNKNOWN
    assert conf <= 0.50

