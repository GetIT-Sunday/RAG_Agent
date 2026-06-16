from typing import List

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkResult(BaseModel):
    chunk_id: int
    score: float
    vector_score: float
    keyword_score: float
    content: str


class SearchResult(BaseModel):
    knowledge_id: int
    title: str
    score: float
    chunks: List[ChunkResult]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    embedding_backend: str
