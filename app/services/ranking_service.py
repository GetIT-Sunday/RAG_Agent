from dataclasses import dataclass
from typing import Dict, List

from app.config import KEYWORD_WEIGHT, VECTOR_WEIGHT
from app.models import KnowledgeChunk


@dataclass
class ChunkScore:
    chunk: KnowledgeChunk
    vector_score: float
    keyword_score: float
    final_score: float


class HybridRanker:
    def __init__(self, vector_weight: float = VECTOR_WEIGHT, keyword_weight: float = KEYWORD_WEIGHT):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def rank(
        self,
        chunks: List[KnowledgeChunk],
        vector_scores: Dict[int, float],
        keyword_scores: Dict[int, float],
    ) -> List[ChunkScore]:
        ranked: List[ChunkScore] = []
        for chunk in chunks:
            vector_score = vector_scores.get(chunk.id, 0.0)
            keyword_score = keyword_scores.get(chunk.id, 0.0)
            final_score = self.vector_weight * vector_score + self.keyword_weight * keyword_score
            ranked.append(ChunkScore(chunk, vector_score, keyword_score, final_score))
        ranked.sort(key=lambda item: item.final_score, reverse=True)
        return ranked
