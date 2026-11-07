import pytest
from app.review.service import review_service
from app.models.document import Document, DocumentStatus, ProcessingStage, DocumentCategory
from app.models.extraction import ExtractedField, ValidationStatus
from app.models.review import ReviewTask, ReviewStatus, ReviewActionType


def test_review_service_workflow(db_session):
    # Setup document and review task
    doc = Document(
        id="doc-test-review-001",
        filename="invoice.pdf",
        original_filename="invoice.pdf",
        file_path="dummy.pdf",
        mime_type="application/pdf",
        file_size_bytes=1000,
        sha256_hash="dummyhashreview123",
        status=DocumentStatus.NEEDS_REVIEW,
        current_stage=ProcessingStage.REVIEW,
        category=DocumentCategory.INVOICE,
    )
    field = ExtractedField(
        id="field-test-001",
        document_id=doc.id,
        field_name="total_amount",
        field_value="2000.00",
        confidence=0.62,
        review_required=True,
        validation_status=ValidationStatus.WARNING,
    )
    task = ReviewTask(
        id="task-test-001",
        document_id=doc.id,
        status=ReviewStatus.PENDING,
        flagged_fields_count=1,
    )

    db_session.add_all([doc, field, task])
    db_session.commit()

    # 1. Update field value (manual override)
    updated_field = review_service.update_field_value(
        session=db_session,
        field_id="field-test-001",
        new_value="2180.00",
        reviewer="auditor_jane",
        notes="Corrected total amount from invoice footer",
    )
    assert updated_field.field_value == "2180.00"
    assert updated_field.is_manual_override is True
    assert updated_field.confidence == 1.0
    assert updated_field.review_required is False

    # Check history logged
    t = review_service.get_review_task(db_session, "task-test-001")
    assert len(t.history) >= 1
    assert t.history[0].action == ReviewActionType.EDIT_FIELD
    assert t.history[0].previous_value == "2000.00"
    assert t.history[0].new_value == "2180.00"

    # 2. Approve document
    approved_task = review_service.approve_review(
        session=db_session,
        review_id="task-test-001",
        reviewer="auditor_jane",
    )
    assert approved_task.status == ReviewStatus.APPROVED
    assert doc.status == DocumentStatus.COMPLETED

