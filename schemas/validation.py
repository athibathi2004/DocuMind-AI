from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.models.validation import ValidationRuleStatus


class ValidationResultResponse(BaseModel):
    id: str
    document_id: str
    rule_name: str
    rule_type: str
    field_name: Optional[str] = None
    status: ValidationRuleStatus
    message: str
    details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

