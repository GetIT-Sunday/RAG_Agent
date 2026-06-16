import asyncio
import json
from typing import AsyncIterator

from sqlalchemy.orm import Session

from app.services.search_service import SearchError, SearchService


def sse_event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_search(db: Session, query: str, top_k: int = 5) -> AsyncIterator[str]:
    yield sse_event("status", {"message": "开始检索", "query": query})
    await asyncio.sleep(0.05)
    try:
        response = SearchService().search(db, query, top_k=top_k, entrypoint="stream")
    except SearchError as exc:
        yield sse_event("error", {"message": str(exc)})
        return
    except Exception as exc:
        yield sse_event("error", {"message": f"检索失败: {exc}"})
        return

    yield sse_event("meta", {"embedding_backend": response.embedding_backend, "count": len(response.results)})
    if not response.results:
        message = "知识库中未找到与该问题足够相关的内容。"
        for char in message:
            yield sse_event("token", {"text": char})
            await asyncio.sleep(0.008)
        yield sse_event("done", {"message": "检索完成，未找到相关内容"})
        return

    for result in response.results:
        yield sse_event("document", {"title": result.title, "score": result.score, "knowledge_id": result.knowledge_id})
        for chunk in result.chunks:
            prefix = f"【{result.title} | score={chunk.score:.3f}】\n"
            for char in prefix + chunk.content + "\n\n":
                yield sse_event("token", {"text": char})
                await asyncio.sleep(0.008)
    yield sse_event("done", {"message": "检索完成"})
