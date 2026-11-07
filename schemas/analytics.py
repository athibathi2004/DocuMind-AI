from typing import Dict, List
from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class AnalyticsOverviewResponse(BaseModel):
    total_documents: int
    processed_documents: int
    pending_reviews: int
    failed_jobs: int
    average_confidence: float
    documents_by_status: List[StatusCount]
    documents_by_category: List[CategoryCount]
    recent_activity_count_24h: int

