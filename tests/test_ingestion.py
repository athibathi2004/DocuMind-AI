import pytest
from pathlib import Path
from app.ingestion.validators import validate_file_upload
from app.ingestion.storage import storage_manager
from app.core.errors import InvalidFileError, DuplicateDocumentError
from app.core.security import sanitize_filename, compute_sha256, mask_sensitive_value


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("test\x00file.png") == "testfile.png"
    assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"
    assert sanitize_filename("spaces in file name.jpg") == "spaces_in_file_name.jpg"


def test_compute_sha256():
    data = b"Hello DocuMind AI"
    h1 = compute_sha256(data)
    h2 = compute_sha256(data)
    assert len(h1) == 64
    assert h1 == h2
    assert h1 != compute_sha256(b"Different data")


def test_mask_sensitive_value():
    assert mask_sensitive_value("passport_number", "A12345678") == "A1*****78"
    assert mask_sensitive_value("document_title", "Invoice 2026") == "Invoice 2026"
    assert mask_sensitive_value("tax_id", "US-94810294") == "US*******94"


def test_validate_file_upload_success():
    # Should not raise
    validate_file_upload("invoice.pdf", "application/pdf", 1024)
    validate_file_upload("passport.png", "image/png", 500000)


def test_validate_file_upload_failures():
    # Empty filename
    with pytest.raises(InvalidFileError, match="Filename is missing"):
        validate_file_upload("", "application/pdf", 1024)

    # Empty file content
    with pytest.raises(InvalidFileError, match="empty"):
        validate_file_upload("invoice.pdf", "application/pdf", 0)

    # Unsupported extension
    with pytest.raises(InvalidFileError, match="not supported"):
        validate_file_upload("malicious.exe", "application/octet-stream", 1024)

    # File size exceeding max limit (25MB)
    with pytest.raises(InvalidFileError, match="exceeds maximum allowed limit"):
        validate_file_upload("huge.pdf", "application/pdf", 30 * 1024 * 1024)


def test_duplicate_document_detection(db_session, tmp_path):
    storage = storage_manager
    content = b"Deterministic test document content for duplicate check"
    sha = compute_sha256(content)

    # Check non-existent
    assert storage.check_duplicate(db_session, sha) is None

    # Ingest document
    from app.services.document_service import document_service
    doc = document_service.ingest_document(
        session=db_session,
        content=content,
        original_filename="first.pdf",
        mime_type="application/pdf",
    )
    assert doc.id is not None

    # Re-ingest exact same content should raise DuplicateDocumentError
    with pytest.raises(DuplicateDocumentError) as exc_info:
        document_service.ingest_document(
            session=db_session,
            content=content,
            original_filename="duplicate.pdf",
            mime_type="application/pdf",
        )
    assert exc_info.value.existing_document_id == doc.id

