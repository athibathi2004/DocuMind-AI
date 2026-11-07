from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.review import ReviewStatus, ReviewActionType


class ReviewHistoryResponse(BaseModel):
    id: str
    task_id: str
    field_id: Optional[str] = None
    field_name: Optional[str] = None
    action: ReviewActionType
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewTaskResponse(BaseModel):
    id: str
    document_id: str
    status: ReviewStatus
    flagged_fields_count: int
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    history: List[ReviewHistoryResponse] = []

    model_config = {"from_attributes": True}


class ReviewActionRequest(BaseModel):
    reviewer: Optional[str] = "admin_reviewer"
    notes: Optional[str] = None

