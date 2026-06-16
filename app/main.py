from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.knowledge_routes import router as knowledge_router
from app.api.search_routes import router as search_router
from app.config import BASE_DIR
from app.database import init_db

app = FastAPI(title="RagAgent Knowledge Base", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(knowledge_router)
app.include_router(search_router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "app" / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True}
