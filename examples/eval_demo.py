from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.models import KnowledgeDocument
from app.services.knowledge_service import KnowledgeService
from app.services.search_service import SearchService

CASES = [
    ("春天", "朱自清《春》", 1),
    ("少年闰土", "鲁迅《故乡》", 1),
    ("小孩子", "鲁迅《故乡》", 2),
]


def ensure_examples(db):
    service = KnowledgeService()
    examples = [
        ("朱自清《春》", ROOT / "examples" / "spring.txt"),
        ("鲁迅《故乡》", ROOT / "examples" / "hometown.txt"),
    ]
    for title, path in examples:
        existing = db.query(KnowledgeDocument).filter(KnowledgeDocument.title == title).first()
        if existing:
            continue
        service.create_document(db, title, path.read_text(encoding="utf-8"), source_type="example")


def main():
    init_db()
    db = SessionLocal()
    try:
        ensure_examples(db)
        service = SearchService()
        print(f"embedding_backend: {service.embedding_service.backend}")
        all_passed = True
        for query, expected, max_rank in CASES:
            response = service.search(db, query, top_k=5)
            titles = [item.title for item in response.results]
            rank = titles.index(expected) + 1 if expected in titles else None
            ok = rank is not None and rank <= max_rank
            all_passed = all_passed and ok
            print(f"query={query} expected={expected} rank={rank} ok={ok}")
            for idx, item in enumerate(response.results[:3], 1):
                print(f"  {idx}. {item.title} score={item.score}")
        raise SystemExit(0 if all_passed else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
