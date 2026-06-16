from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ChunkConfig:
    min_chars: int = 120
    target_chars: int = 650
    max_chars: int = 1000
    overlap_chars: int = 120


class ChunkService:
    def __init__(self, config: ChunkConfig | None = None):
        self.config = config or ChunkConfig()

    def clean_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def split_paragraphs(self, text: str) -> List[str]:
        text = self.clean_text(text)
        if not text:
            return []
        rough = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
        paragraphs: List[str] = []
        for part in rough:
            if len(part) <= self.config.max_chars:
                paragraphs.append(part)
                continue
            paragraphs.extend(self._split_long_paragraph(part))
        return paragraphs

    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        sentences = [s.strip() for s in re.split(r"(?<=[。！？!?；;])", paragraph) if s.strip()]
        if not sentences:
            return [paragraph[i : i + self.config.max_chars] for i in range(0, len(paragraph), self.config.max_chars)]
        pieces: List[str] = []
        current = ""
        for sentence in sentences:
            if current and len(current) + len(sentence) > self.config.max_chars:
                pieces.append(current)
                current = sentence
            else:
                current += sentence
        if current:
            pieces.append(current)
        return pieces

    def create_chunks(self, text: str) -> List[str]:
        paragraphs = self.split_paragraphs(text)
        if not paragraphs:
            return []

        chunks: List[str] = []
        current_parts: List[str] = []
        current_len = 0

        for paragraph in paragraphs:
            p_len = len(paragraph)
            should_flush = current_parts and current_len + p_len > self.config.target_chars
            if should_flush and current_len >= self.config.min_chars:
                chunks.append("\n".join(current_parts).strip())
                current_parts, current_len = self._make_overlap(current_parts)
            current_parts.append(paragraph)
            current_len += p_len

            if current_len >= self.config.max_chars:
                chunks.append("\n".join(current_parts).strip())
                current_parts, current_len = self._make_overlap(current_parts)

        if current_parts:
            candidate = "\n".join(current_parts).strip()
            if chunks and len(candidate) < self.config.min_chars:
                chunks[-1] = (chunks[-1] + "\n" + candidate).strip()
            else:
                chunks.append(candidate)

        return [chunk for chunk in chunks if chunk]

    def _make_overlap(self, parts: List[str]) -> tuple[List[str], int]:
        overlap: List[str] = []
        total = 0
        for part in reversed(parts):
            overlap.insert(0, part)
            total += len(part)
            if total >= self.config.overlap_chars:
                break
        return overlap, total
