from __future__ import annotations

import hashlib
import os
import json
import math
import re
from functools import lru_cache
from typing import Iterable, List

import numpy as np

from app.config import ALLOW_MODEL_DOWNLOAD, EMBEDDING_MODEL_NAME, ENABLE_EMBEDDING_FALLBACK, FORCE_EMBEDDING_FALLBACK
from app.services.keyword_service import expand_query_terms, tokenize_text


class EmbeddingService:
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.backend = "fallback-hash"
        self.dimension = 384
        self._load_model()

    def _load_model(self) -> None:
        if FORCE_EMBEDDING_FALLBACK:
            self.model = None
            self.backend = "fallback-hash"
            return

        os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "3")
        os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "10")
        try:
            from sentence_transformers import SentenceTransformer

            try:
                self.model = SentenceTransformer(self.model_name, local_files_only=True)
            except Exception:
                if not ALLOW_MODEL_DOWNLOAD:
                    raise
                self.model = SentenceTransformer(self.model_name)
            dim = self.model.get_sentence_embedding_dimension()
            self.dimension = int(dim or self.dimension)
            self.backend = self.model_name
        except Exception:
            if not ENABLE_EMBEDDING_FALLBACK:
                raise
            self.model = None
            self.backend = "fallback-hash"

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        items = list(texts)
        if not items:
            return []
        if self.model is not None:
            vectors = self.model.encode(items, normalize_embeddings=True)
            return [np.asarray(v, dtype=float).tolist() for v in vectors]
        return [self._fallback_vector(text) for text in items]

    def encode_one(self, text: str) -> List[float]:
        return self.encode([text])[0]

    def _fallback_vector(self, text: str) -> List[float]:
        tokens = tokenize_text(text)
        expanded = tokens + expand_query_terms(text)
        vector = np.zeros(self.dimension, dtype=float)
        for token in expanded:
            if not token:
                continue
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dimension
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[idx] += sign
        # Character bigrams help Chinese short queries when tokenization is weak.
        compact = re.sub(r"\s+", "", text)
        for i in range(max(0, len(compact) - 1)):
            gram = compact[i : i + 2]
            digest = hashlib.sha1(gram.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dimension
            vector[idx] += 0.4
        norm = math.sqrt(float(np.dot(vector, vector)))
        if norm == 0:
            return vector.tolist()
        return (vector / norm).tolist()


def dumps_embedding(vector: List[float]) -> str:
    return json.dumps(vector, ensure_ascii=False, separators=(",", ":"))


def loads_embedding(raw: str | None) -> List[float]:
    if not raw:
        return []
    return json.loads(raw)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
