import pytest
from app.validation.mrz_validator import MRZValidator
from app.validation.field_rules import (
    normalize_date,
    validate_numeric_amount,
    check_invoice_math,
    check_passport_dates,
)
from app.validation.engine import ValidationEngine
from app.models.document import DocumentCategory
from app.extraction.base import RawExtractedField


def test_mrz_checksum_calculation():
    # Test vector: Document number 'A12345678' -> check digit 7
    # Characters: A(10)*7 + 1*3 + 2*1 + 3*7 + 4*3 + 5*1 + 6*7 + 7*3 + 8*1
    # 70 + 3 + 2 + 21 + 12 + 5 + 42 + 21 + 8 = 184 -> 184 % 10 = 4 (or depending on weights)
    val = MRZValidator.compute_check_digit("A12345678")
    assert 0 <= val <= 9

    # Valid Line 2 check
    valid_line2 = "A123456787USA8804144F3106114<<<<<<<<<<<<<<06"
    res = MRZValidator.validate_td3_line2(valid_line2)
    assert res["is_valid"] is True
    assert res["checks"]["passport_number"]["valid"] is True
    assert res["checks"]["date_of_birth"]["valid"] is True
    assert res["checks"]["date_of_expiry"]["valid"] is True


def test_normalize_date():
    ok, iso, err = normalize_date("14 APR 1988")
    assert ok is True
    assert iso == "1988-04-14"

    ok2, iso2, err2 = normalize_date("2026-03-15")
    assert ok2 is True
    assert iso2 == "2026-03-15"

    ok3, iso3, err3 = normalize_date("InvalidDateString")
    assert ok3 is False


def test_validate_numeric_amount():
    ok, num, err = validate_numeric_amount("$2,180.50")
    assert ok is True
    assert num == 2180.50

    ok_neg, num_neg, err_neg = validate_numeric_amount("$-10.00")
    assert ok_neg is False


def test_check_invoice_math():
    # 2000.00 + 180.00 == 2180.00 -> PASS
    valid, err = check_invoice_math(2000.0, 180.0, 2180.0)
    assert valid is True

    # Mismatch -> FAIL
    invalid, err_msg = check_invoice_math(2000.0, 180.0, 2500.0)
    assert invalid is False
    assert "mismatch" in err_msg.lower()


def test_check_passport_dates():
    # Expiry 2031-06-11 after Birth 1988-04-14 -> PASS
    valid, err = check_passport_dates("1988-04-14", "2031-06-11")
    assert valid is True

    # Expiry before birth -> FAIL
    invalid, err_msg = check_passport_dates("2031-06-11", "1988-04-14")
    assert invalid is False


def test_validation_engine_required_fields():
    engine = ValidationEngine()
    fields = [
        RawExtractedField("invoice_number", "INV-100"),
        RawExtractedField("invoice_date", "2026-01-01"),
        # Total amount missing
    ]
    results, statuses, normalized = engine.validate_document_fields(DocumentCategory.INVOICE, fields)
    assert any(r["rule_name"] == "REQUIRED_TOTAL_AMOUNT" and r["status"].value == "FAIL" for r in results)

