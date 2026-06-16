from collections import defaultdict
from typing import Dict, List

from app.config import MIN_RELEVANCE_SCORE
from app.schemas.search import ChunkResult, SearchResult
from app.services.ranking_service import ChunkScore


class DocumentAggregator:
    def aggregate(self, ranked_chunks: List[ChunkScore], top_k: int, min_score: float = MIN_RELEVANCE_SCORE) -> List[SearchResult]:
        grouped: Dict[int, List[ChunkScore]] = defaultdict(list)
        relevant_chunks = [item for item in ranked_chunks if item.final_score >= min_score]
        for item in relevant_chunks[: max(top_k * 4, 12)]:
            grouped[item.chunk.document_id].append(item)

        results: List[SearchResult] = []
        for document_id, items in grouped.items():
            items.sort(key=lambda item: item.final_score, reverse=True)
            top_items = items[:3]
            max_score = top_items[0].final_score
            avg_top = sum(item.final_score for item in top_items) / len(top_items)
            document_score = 0.7 * max_score + 0.3 * avg_top
            document = top_items[0].chunk.document
            results.append(
                SearchResult(
                    knowledge_id=document_id,
                    title=document.title,
                    score=round(float(document_score), 6),
                    chunks=[
                        ChunkResult(
                            chunk_id=item.chunk.id,
                            score=round(float(item.final_score), 6),
                            vector_score=round(float(item.vector_score), 6),
                            keyword_score=round(float(item.keyword_score), 6),
                            content=item.chunk.content,
                        )
                        for item in top_items
                    ],
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]
