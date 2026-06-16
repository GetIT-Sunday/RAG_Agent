from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import KnowledgeChunk, KnowledgeDocument
from app.services.chunk_service import ChunkService
from app.services.embedding_service import dumps_embedding, get_embedding_service


class KnowledgeService:
    def __init__(self):
        self.chunk_service = ChunkService()
        self.embedding_service = get_embedding_service()

    def create_document(self, db: Session, title: str, content: str, source_type: str = "text") -> KnowledgeDocument:
        title = title.strip()
        content = content.strip()
        if not title:
            raise ValueError("title 不能为空")
        if not content:
            raise ValueError("content 不能为空")
        document = KnowledgeDocument(title=title, content=content, source_type=source_type)
        db.add(document)
        db.flush()
        self._replace_chunks(db, document, content)
        db.commit()
        db.refresh(document)
        return document

    def update_document(self, db: Session, document: KnowledgeDocument, title: str, content: str) -> KnowledgeDocument:
        title = title.strip()
        content = content.strip()
        if not title:
            raise ValueError("title 不能为空")
        if not content:
            raise ValueError("content 不能为空")
        document.title = title
        document.content = content
        self._replace_chunks(db, document, content)
        db.commit()
        db.refresh(document)
        return document

    def _replace_chunks(self, db: Session, document: KnowledgeDocument, content: str) -> None:
        db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()
        chunk_texts = self.chunk_service.create_chunks(content)
        vectors = self.embedding_service.encode(chunk_texts)
        for index, chunk_text in enumerate(chunk_texts):
            db.add(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk_text,
                    embedding=dumps_embedding(vectors[index]) if index < len(vectors) else None,
                    char_count=len(chunk_text),
                )
            )

    def count_chunks(self, db: Session, document_id: int) -> int:
        return db.query(func.count(KnowledgeChunk.id)).filter(KnowledgeChunk.document_id == document_id).scalar() or 0
