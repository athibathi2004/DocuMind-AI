import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Enum,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class ValidationStatus(str, enum.Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    WARNING = "WARNING"
    MISSING = "MISSING"


class ExtractedField(Base):
    """Structured field extracted from document with provenance and confidence scores."""

    __tablename__ = "extracted_fields"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(String(50), default="string", nullable=False)

    # Multi-component confidence
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # Composite
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus), default=ValidationStatus.VALID, nullable=False
    )
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    # Provenance
    source_page: Mapped[Optional[int]] = mapped_column(Integer, default=1, nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Human-in-the-loop tracking
    is_manual_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="extracted_fields")

