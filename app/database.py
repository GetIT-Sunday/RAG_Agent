from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.models import chunk, knowledge, search_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()


def _run_sqlite_migrations() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        chunk_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(knowledge_chunks)"))}
        if "embedding_json" not in chunk_columns:
            conn.execute(text("ALTER TABLE knowledge_chunks ADD COLUMN embedding_json TEXT"))
        if "embedding" in chunk_columns:
            conn.execute(
                text(
                    "UPDATE knowledge_chunks "
                    "SET embedding_json = embedding "
                    "WHERE embedding_json IS NULL AND embedding IS NOT NULL"
                )
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
