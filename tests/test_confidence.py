import pytest
from app.confidence.assessor import ConfidenceAssessor
from app.extraction.base import RawExtractedField
from app.models.extraction import ValidationStatus


def test_confidence_assessment_high():
    assessor = ConfidenceAssessor(threshold=0.70)
    field = RawExtractedField(
        field_name="invoice_number",
        field_value="INV-2026-001",
        ocr_confidence=0.95,
        extraction_confidence=0.96,
    )
    comp_conf, val_conf, rev_req = assessor.assess_field(field, ValidationStatus.VALID)

    # 0.35 * 0.95 + 0.40 * 0.96 + 0.25 * 1.0 = 0.3325 + 0.384 + 0.25 = 0.9665
    assert comp_conf >= 0.95
    assert val_conf == 1.0
    assert rev_req is False


def test_confidence_assessment_low_flags_review():
    assessor = ConfidenceAssessor(threshold=0.70)
    field = RawExtractedField(
        field_name="tax_amount",
        field_value="$12.00",
        ocr_confidence=0.50,
        extraction_confidence=0.55,
    )
    comp_conf, val_conf, rev_req = assessor.assess_field(field, ValidationStatus.WARNING)

    assert comp_conf < 0.70
    assert rev_req is True


def test_missing_field_zero_confidence():
    assessor = ConfidenceAssessor()
    field = RawExtractedField(
        field_name="passport_number",
        field_value=None,
        is_missing=True,
    )
    comp_conf, val_conf, rev_req = assessor.assess_field(field, ValidationStatus.MISSING)
    assert comp_conf == 0.0
    assert rev_req is True

