from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import KnowledgeDocument
from app.services.embedding_service import get_embedding_service
from app.services.knowledge_service import KnowledgeService
from app.services.search_service import SearchService


def test_search_service_aggregates_documents():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        service = KnowledgeService()
        service.create_document(db, "朱自清《春》", "东风来了，春天的脚步近了。小草绿了，花开了。")
        service.create_document(db, "鲁迅《故乡》", "少年闰土项带银圈，在瓜地里看猹。他是儿时的伙伴，也是孩子时代的记忆。")
        response = SearchService().search(db, "少年闰土", top_k=2)
        assert response.results[0].title == "鲁迅《故乡》"
    finally:
        db.close()


def test_search_service_returns_empty_for_out_of_domain_query(monkeypatch):
    monkeypatch.setenv("FORCE_EMBEDDING_FALLBACK", "true")
    get_embedding_service.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        service = KnowledgeService()
        service.create_document(db, "朱自清《春》", "东风来了，春天的脚步近了。小草绿了，花开了。")
        service.create_document(db, "鲁迅《故乡》", "少年闰土项带银圈，在瓜地里看猹。他是儿时的伙伴，也是孩子时代的记忆。")
        response = SearchService().search(db, "如何配置 Kubernetes Ingress", top_k=2)
        assert response.results == []
    finally:
        db.close()
        get_embedding_service.cache_clear()
