from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeCreate, KnowledgeItem, KnowledgeListResponse, KnowledgeUpdate
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def to_item(db: Session, document: KnowledgeDocument) -> KnowledgeItem:
    chunk_count = db.query(func.count(KnowledgeChunk.id)).filter(KnowledgeChunk.document_id == document.id).scalar() or 0
    return KnowledgeItem(
        id=document.id,
        title=document.title,
        content=document.content,
        source_type=document.source_type,
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_count=chunk_count,
    )


@router.get("", response_model=KnowledgeListResponse)
def list_knowledge(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return KnowledgeListResponse(items=[to_item(db, item) for item in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=KnowledgeItem)
def create_knowledge(payload: KnowledgeCreate, db: Session = Depends(get_db)):
    try:
        document = KnowledgeService().create_document(db, payload.title, payload.content, source_type="text")
        return to_item(db, document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{knowledge_id}", response_model=KnowledgeItem)
def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, knowledge_id)
    if document is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return to_item(db, document)


@router.put("/{knowledge_id}", response_model=KnowledgeItem)
def update_knowledge(knowledge_id: int, payload: KnowledgeUpdate, db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, knowledge_id)
    if document is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    try:
        updated = KnowledgeService().update_document(db, document, payload.title, payload.content)
        return to_item(db, updated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{knowledge_id}")
def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, knowledge_id)
    if document is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    db.delete(document)
    db.commit()
    return {"ok": True, "deleted_id": knowledge_id}


@router.post("/upload", response_model=KnowledgeItem)
async def upload_knowledge(
    title: str = Form(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix != ".txt":
        raise HTTPException(status_code=400, detail="当前仅支持 txt 文件")
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("gb18030", errors="ignore")
    final_title = title.strip() or Path(file.filename or "未命名知识库").stem
    try:
        document = KnowledgeService().create_document(db, final_title, content, source_type="txt")
        return to_item(db, document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
