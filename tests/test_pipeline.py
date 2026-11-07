import pytest
from app.pipeline.orchestrator import pipeline_orchestrator
from app.services.document_service import document_service
from app.models.document import DocumentStatus, DocumentCategory
from app.core.errors import ProcessingError


def test_end_to_end_pipeline_invoice(db_session, sample_data_dir):
    invoice_path = sample_data_dir / "sample_invoice.pdf"
    if not invoice_path.exists():
        pytest.skip("sample_invoice.pdf not found")

    with open(invoice_path, "rb") as f:
        content = f.read()

    doc = document_service.ingest_document(
        session=db_session,
        content=content,
        original_filename="test_invoice.pdf",
        mime_type="application/pdf",
    )
    assert doc.id is not None

    processed = pipeline_orchestrator.process_document(
        session=db_session,
        document_id=doc.id,
        ocr_provider="mock",
    )

    assert processed.category == DocumentCategory.INVOICE
    assert len(processed.extracted_fields) > 0
    assert len(processed.validation_results) > 0
    assert processed.overall_confidence > 0.70
    assert len(processed.processing_jobs) >= 1
    assert processed.processing_jobs[0].status == "SUCCESS"


def test_pipeline_missing_file_failure(db_session):
    doc = document_service.ingest_document(
        session=db_session,
        content=b"Dummy content for missing file test",
        original_filename="missing_test.pdf",
        mime_type="application/pdf",
    )
    # Point file_path to nonexistent path
    doc.file_path = "nonexistent_file_path_xyz.pdf"
    db_session.commit()

    with pytest.raises(ProcessingError):
        pipeline_orchestrator.process_document(
            session=db_session,
            document_id=doc.id,
            ocr_provider="mock",
        )

    # Verify status changed to FAILED
    detail = document_service.get_document(db_session, doc.id)
    assert detail.status == DocumentStatus.FAILED
    assert detail.error_message is not None

