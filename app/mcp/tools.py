import concurrent.futures
from typing import Any, Dict

from app.config import SEARCH_TIMEOUT_SECONDS
from app.database import SessionLocal, init_db
from app.services.search_service import SearchError, SearchService


def search_knowledge_tool(query: str, top_k: int = 5) -> Dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "query 不能为空", "results": []}
    top_k = max(1, min(int(top_k or 5), 20))

    def _run():
        init_db()
        db = SessionLocal()
        try:
            response = SearchService().search(db, query, top_k=top_k, entrypoint="mcp")
            if not response.results:
                return {
                    "ok": True,
                    "query": response.query,
                    "embedding_backend": response.embedding_backend,
                    "answer": "不知道，知识库中未找到与该问题足够相关的内容。",
                    "fallback_to_base_model": True,
                    "suggested_next_action": "answer_with_base_model",
                    "agent_instruction": (
                        "知识库未命中。请明确告诉用户该问题未在知识库中找到相关内容；"
                        "如果用户需要答案，请基于你的基础模型能力继续回答，并说明该回答不是来自知识库。"
                    ),
                    "results": [],
                }
            return {
                "ok": True,
                "query": response.query,
                "embedding_backend": response.embedding_backend,
                "answer": None,
                "fallback_to_base_model": False,
                "suggested_next_action": "answer_from_knowledge_results",
                "agent_instruction": "请基于 results 中的知识库片段回答用户问题，并优先引用 title 和 content。",
                "results": [item.model_dump() for item in response.results],
            }
        except SearchError as exc:
            return {"ok": False, "error": str(exc), "results": []}
        except Exception as exc:
            return {"ok": False, "error": f"检索失败: {exc}", "results": []}
        finally:
            db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            return future.result(timeout=SEARCH_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            return {"ok": False, "error": "工具调用超时", "results": []}
