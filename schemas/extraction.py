from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.extraction import ValidationStatus


class ExtractedFieldBase(BaseModel):
    field_name: str
    field_value: Optional[str] = None
    normalized_value: Optional[str] = None
    field_type: str = "string"
    confidence: float = Field(ge=0.0, le=1.0)
    ocr_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    validation_confidence: Optional[float] = None
    validation_status: ValidationStatus = ValidationStatus.VALID
    review_required: bool = False
    source_page: Optional[int] = 1
    source_text: Optional[str] = None
    bounding_box: Optional[Dict[str, Any]] = None
    is_manual_override: bool = False
    original_value: Optional[str] = None


class ExtractedFieldResponse(ExtractedFieldBase):
    id: str
    document_id: str

    model_config = {"from_attributes": True}


class ExtractedFieldUpdate(BaseModel):
    field_value: str
    reviewer_notes: Optional[str] = None
    reviewer: Optional[str] = "reviewer"

