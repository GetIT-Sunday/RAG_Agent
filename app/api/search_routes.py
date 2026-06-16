from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchError, SearchService
from app.services.stream_service import stream_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    try:
        return SearchService().search(db, payload.query, payload.top_k, entrypoint="web")
    except SearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"检索失败: {exc}") from exc


@router.get("/stream")
def search_stream(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return StreamingResponse(stream_search(db, query, top_k), media_type="text/event-stream")
