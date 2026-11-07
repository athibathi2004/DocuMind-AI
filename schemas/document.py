from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.models.document import DocumentStatus, ProcessingStage, DocumentCategory
from app.schemas.ocr import OCRResultResponse, TextBlockResponse
from app.schemas.extraction import ExtractedFieldResponse
from app.schemas.validation import ValidationResultResponse
from app.schemas.review import ReviewTaskResponse


class DocumentPageResponse(BaseModel):
    id: str
    page_number: int
    image_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    dpi: Optional[int] = None
    preprocessed_path: Optional[str] = None
    text_blocks: List[TextBlockResponse] = []

    model_config = {"from_attributes": True}


class ProcessingJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    stage: ProcessingStage
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    diagnostics: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    page_count: int
    status: DocumentStatus
    current_stage: ProcessingStage
    category: DocumentCategory
    classification_confidence: Optional[float] = None
    classification_explanation: Optional[str] = None
    overall_confidence: Optional[float] = None
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    pages: List[DocumentPageResponse] = []
    extracted_fields: List[ExtractedFieldResponse] = []
    validation_results: List[ValidationResultResponse] = []
    ocr_results: List[OCRResultResponse] = []
    processing_jobs: List[ProcessingJobResponse] = []
    review_tasks: List[ReviewTaskResponse] = []

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]

