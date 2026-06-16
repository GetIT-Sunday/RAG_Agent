from __future__ import annotations

import time
from typing import Dict, List

import numpy as np
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk, KnowledgeDocument, SearchLog
from app.schemas.search import SearchResponse
from app.services.document_aggregator import DocumentAggregator
from app.services.embedding_service import get_embedding_service, loads_embedding
from app.services.keyword_service import KeywordService
from app.services.ranking_service import HybridRanker


class SearchError(Exception):
    pass


class SearchService:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.keyword_service = KeywordService()
        self.ranker = HybridRanker()
        self.aggregator = DocumentAggregator()

    def search(self, db: Session, query: str, top_k: int = 5, entrypoint: str = "api") -> SearchResponse:
        started_at = time.perf_counter()
        query = (query or "").strip()
        if not query:
            self._log_search(db, query, top_k, entrypoint, 0, 0.0, "query 不能为空")
            raise SearchError("query 不能为空")

        chunks = db.query(KnowledgeChunk).join(KnowledgeDocument).all()
        if not chunks:
            self._log_search(db, query, top_k, entrypoint, 0, 0.0, "知识库为空")
            raise SearchError("知识库为空，请先上传或创建知识内容")

        query_vector = self.embedding_service.encode_one(query)
        vector_scores = self._vector_scores(query_vector, chunks)
        keyword_scores = self.keyword_service.score(query, {chunk.id: chunk.content for chunk in chunks})
        if self.embedding_service.backend == "fallback-hash":
            vector_scores = {
                chunk_id: score if keyword_scores.get(chunk_id, 0.0) > 0 else 0.0
                for chunk_id, score in vector_scores.items()
            }
        ranked_chunks = self.ranker.rank(chunks, vector_scores, keyword_scores)
        results = self.aggregator.aggregate(ranked_chunks, top_k)

        duration_ms = (time.perf_counter() - started_at) * 1000
        self._log_search(db, query, top_k, entrypoint, len(results), duration_ms, None)
        return SearchResponse(
            query=query,
            results=results,
            embedding_backend=self.embedding_service.backend,
        )

    def _vector_scores(self, query_vector: List[float], chunks: List[KnowledgeChunk]) -> Dict[int, float]:
        q = np.asarray(query_vector, dtype=float)
        q_norm = float(np.linalg.norm(q))
        scores: Dict[int, float] = {}
        if q_norm == 0:
            return {chunk.id: 0.0 for chunk in chunks}

        raw_values: Dict[int, float] = {}
        for chunk in chunks:
            vector = loads_embedding(chunk.embedding)
            if not vector:
                raw_values[chunk.id] = 0.0
                continue
            v = np.asarray(vector, dtype=float)
            if v.shape != q.shape:
                raw_values[chunk.id] = 0.0
                continue
            denom = q_norm * float(np.linalg.norm(v))
            raw = 0.0 if denom == 0 else float(np.dot(q, v) / denom)
            raw_values[chunk.id] = max(0.0, raw)

        max_score = max(raw_values.values(), default=0.0)
        if max_score <= 0:
            return {chunk.id: 0.0 for chunk in chunks}
        for chunk_id, value in raw_values.items():
            scores[chunk_id] = value / max_score
        return scores

    def _log_search(
        self,
        db: Session,
        query: str,
        top_k: int,
        entrypoint: str,
        result_count: int,
        duration_ms: float,
        error: str | None,
    ) -> None:
        db.add(
            SearchLog(
                query=query or "",
                entrypoint=entrypoint,
                top_k=top_k,
                result_count=result_count,
                embedding_backend=self.embedding_service.backend,
                duration_ms=round(float(duration_ms), 3),
                error=error,
            )
        )
        db.commit()
