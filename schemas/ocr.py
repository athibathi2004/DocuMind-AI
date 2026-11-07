from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.ocr import BlockType


class TextBlockBase(BaseModel):
    page_number: int
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    block_type: BlockType = BlockType.LINE
    reading_order: int = 0
    bbox_x_min: float
    bbox_y_min: float
    bbox_x_max: float
    bbox_y_max: float
    polygon: Optional[List[List[float]]] = None


class TextBlockResponse(TextBlockBase):
    id: str
    page_id: str

    model_config = {"from_attributes": True}


class OCRResultResponse(BaseModel):
    id: str
    document_id: str
    provider: str
    page_count: int
    total_blocks: int
    raw_text: str
    average_confidence: float
    execution_time_ms: int
    diagnostics: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

