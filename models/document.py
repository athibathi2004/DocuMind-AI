import enum
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Float,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ocr import OCRResult, TextBlock
    from app.models.extraction import ExtractedField
    from app.models.validation import ValidationResult
    from app.models.review import ReviewTask


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class ProcessingStage(str, enum.Enum):
    UPLOAD = "UPLOAD"
    PREPROCESSING = "PREPROCESSING"
    OCR = "OCR"
    LAYOUT = "LAYOUT"
    CLASSIFICATION = "CLASSIFICATION"
    EXTRACTION = "EXTRACTION"
    CONFIDENCE = "CONFIDENCE"
    VALIDATION = "VALIDATION"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentCategory(str, enum.Enum):
    PASSPORT = "PASSPORT"
    INVOICE = "INVOICE"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    BUSINESS_DOCUMENT = "BUSINESS_DOCUMENT"
    CONTRACT = "CONTRACT"
    GENERAL_DOCUMENT = "GENERAL_DOCUMENT"
    UNKNOWN = "UNKNOWN"


class Document(Base):
    """Primary document representation storing ingestion metadata, classification, and status."""

    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING, index=True, nullable=False
    )
    current_stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage), default=ProcessingStage.UPLOAD, nullable=False
    )

    category: Mapped[DocumentCategory] = mapped_column(
        Enum(DocumentCategory), default=DocumentCategory.UNKNOWN, index=True, nullable=False
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    classification_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    ocr_results: Mapped[List["OCRResult"]] = relationship(
        "OCRResult", back_populates="document", cascade="all, delete-orphan"
    )
    extracted_fields: Mapped[List["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="document", cascade="all, delete-orphan"
    )
    validation_results: Mapped[List["ValidationResult"]] = relationship(
        "ValidationResult", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[List["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )
    review_tasks: Mapped[List["ReviewTask"]] = relationship(
        "ReviewTask", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentPage(Base):
    """Individual page of a document, tracking preprocessed images and dimensions."""

    __tablename__ = "document_pages"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dpi: Mapped[Optional[int]] = mapped_column(Integer, default=200, nullable=True)
    preprocessed_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    text_blocks: Mapped[List["TextBlock"]] = relationship(
        "TextBlock", back_populates="page", cascade="all, delete-orphan"
    )


class ProcessingJob(Base):
    """Tracks end-to-end processing execution lifecycle, stages, duration, and diagnostics."""

    __tablename__ = "processing_jobs"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False)
    stage: Mapped[ProcessingStage] = mapped_column(Enum(ProcessingStage), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnostics: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="processing_jobs")

