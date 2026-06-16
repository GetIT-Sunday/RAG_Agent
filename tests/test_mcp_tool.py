from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.mcp import tools
from app.services.embedding_service import get_embedding_service
from app.services.knowledge_service import KnowledgeService


def test_mcp_tool_suggests_base_model_fallback(monkeypatch):
    monkeypatch.setenv("FORCE_EMBEDDING_FALLBACK", "true")
    get_embedding_service.cache_clear()

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    monkeypatch.setattr(tools, "SessionLocal", lambda: db)
    monkeypatch.setattr(tools, "init_db", lambda: None)
    try:
        KnowledgeService().create_document(db, "朱自清《春》", "东风来了，春天的脚步近了。")
        response = tools.search_knowledge_tool("如何配置 Kubernetes Ingress", top_k=2)
        assert response["ok"] is True
        assert response["results"] == []
        assert response["fallback_to_base_model"] is True
        assert response["suggested_next_action"] == "answer_with_base_model"
        assert "基础模型" in response["agent_instruction"]
    finally:
        db.close()
        get_embedding_service.cache_clear()
