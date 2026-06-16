from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class KnowledgeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class KnowledgeUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class KnowledgeItem(BaseModel):
    id: int
    title: str
    content: str
    source_type: str
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0

    model_config = {"from_attributes": True}


class KnowledgeListResponse(BaseModel):
    items: List[KnowledgeItem]
    total: int
    page: int
    page_size: int
