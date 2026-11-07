import pytest
from app.extraction.passport import PassportExtractor
from app.extraction.invoice import InvoiceExtractor
from app.extraction.general import GeneralExtractor
from app.ocr.base import OCRPageData, TextBlockData, BoundingBox
from app.layout.text_blocks import LayoutStructure


def test_passport_extraction():
    extractor = PassportExtractor()
    blocks = [
        TextBlockData("PASSPORT / PASSEPORT", BoundingBox(10, 10, 200, 30), 0.98, 1),
        TextBlockData("Passport No: A12345678", BoundingBox(10, 40, 250, 60), 0.95, 1),
        TextBlockData("Surname: HENDRICKS", BoundingBox(10, 70, 250, 90), 0.95, 1),
        TextBlockData("Given Names: ELEANOR JANE", BoundingBox(10, 100, 300, 120), 0.94, 1),
        TextBlockData("Nationality: UNITED STATES OF AMERICA", BoundingBox(10, 130, 400, 150), 0.96, 1),
        TextBlockData("Date of Birth: 14 APR 1988", BoundingBox(10, 160, 280, 180), 0.93, 1),
        TextBlockData("Sex: F", BoundingBox(10, 190, 80, 210), 0.97, 1),
        TextBlockData("Date of Expiration: 11 JUN 2031", BoundingBox(10, 220, 300, 240), 0.92, 1),
        TextBlockData("P<USAHENDRICKS<<ELEANOR<JANE<<<<<<<<<<<<<<<<", BoundingBox(10, 280, 500, 300), 0.98, 1),
        TextBlockData("A123456787USA8804144F3106114<<<<<<<<<<<<<<06", BoundingBox(10, 310, 500, 330), 0.98, 1),
    ]
    page = OCRPageData(1, 800, 1000, blocks=blocks)
    fields = extractor.extract([page], LayoutStructure())

    f_map = {f.field_name: f.field_value for f in fields}
    assert f_map["passport_number"] == "A12345678"
    assert f_map["surname"] == "HENDRICKS"
    assert f_map["given_names"] == "ELEANOR JANE"
    assert f_map["full_name"] == "ELEANOR JANE HENDRICKS"
    assert f_map["sex"] == "F"
    assert f_map["nationality"] == "UNITED STATES OF AMERICA"
    assert "1988" in f_map["date_of_birth"]
    assert "2031" in f_map["date_of_expiry"]
    assert f_map["mrz_line1"] is not None
    assert f_map["mrz_line2"] is not None


def test_invoice_extraction():
    extractor = InvoiceExtractor()
    blocks = [
        TextBlockData("INVOICE", BoundingBox(10, 10, 100, 30), 0.99, 1, "HEADING"),
        TextBlockData("Acme Supplies Inc.", BoundingBox(10, 40, 200, 60), 0.96, 1, "HEADING"),
        TextBlockData("Invoice Number: INV-2026-001", BoundingBox(10, 70, 300, 90), 0.95, 1),
        TextBlockData("Invoice Date: 2026-03-15", BoundingBox(10, 100, 250, 120), 0.95, 1),
        TextBlockData("Due Date: 2026-04-15", BoundingBox(10, 130, 220, 150), 0.94, 1),
        TextBlockData("Bill To: Beta Corp", BoundingBox(10, 160, 220, 180), 0.93, 1),
        TextBlockData("Subtotal: $1,000.00", BoundingBox(10, 220, 250, 240), 0.94, 1),
        TextBlockData("Tax: $100.00", BoundingBox(10, 250, 200, 270), 0.92, 1),
        TextBlockData("Total Amount: $1,100.00", BoundingBox(10, 280, 280, 300), 0.97, 1),
    ]
    page = OCRPageData(1, 800, 1000, blocks=blocks)
    fields = extractor.extract([page], LayoutStructure())

    f_map = {f.field_name: f.field_value for f in fields}
    assert f_map["invoice_number"] == "INV-2026-001"
    assert f_map["invoice_date"] == "2026-03-15"
    assert f_map["due_date"] == "2026-04-15"
    assert f_map["customer_name"] == "Beta Corp"
    assert f_map["subtotal"] == "1000.00"
    assert f_map["tax"] == "100.00"
    assert f_map["total_amount"] == "1100.00"
    assert f_map["currency"] == "USD"

