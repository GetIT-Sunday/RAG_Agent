from __future__ import annotations

import re
import ssl
import sys
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.models import KnowledgeDocument
from app.services.knowledge_service import KnowledgeService


@dataclass(frozen=True)
class SeedDocument:
    title: str
    author: str
    source_url: str
    parser: str
    fallback_path: str | None = None


DOCUMENTS = [
    SeedDocument(
        title="朱自清《春》",
        author="朱自清",
        source_url="https://zh.wikisource.org/wiki/%E6%98%A5_(%E6%9C%B1%E8%87%AA%E6%B8%85)?action=raw",
        parser="wikisource_raw",
    ),
    SeedDocument(
        title="鲁迅《故乡》",
        author="鲁迅",
        source_url="https://www.ruiwen.com/wenxue/luxun/5000.html",
        parser="ruiwen_hometown",
        fallback_path="examples/hometown.txt",
    ),
    SeedDocument(
        title="鲁迅《从百草园到三味书屋》",
        author="鲁迅",
        source_url="https://zh.wikisource.org/wiki/%E5%BE%9E%E7%99%BE%E8%8D%89%E5%9C%92%E5%88%B0%E4%B8%89%E5%91%B3%E6%9B%B8%E5%B1%8B?action=raw",
        parser="wikisource_raw",
    ),
    SeedDocument(
        title="鲁迅《社戏》",
        author="鲁迅",
        source_url="https://zh.wikisource.org/wiki/%E7%A4%BE%E6%88%B2?action=raw",
        parser="wikisource_raw",
    ),
]


def fetch_text(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RagAgentSeed/0.1 (+local selection project)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return resp.read()


def strip_wikisource_raw(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"\{\{header.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\{\{Not-PD-US-old.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\{\{Pd/1923.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\{\{Textquality.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\{\{right\|.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"\{\{gap\}\}", "", text)
    text = re.sub(r"\{\{另\|([^|{}]+)\|([^|{}]+)\}\}", r"\1", text)
    text = re.sub(r"</?onlyinclude>", "", text)
    text = re.sub(r"&emsp;|&nbsp;", " ", text)
    text = re.sub(r"\[\[([^|\]]+)\|([^|\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)
    return normalize_text(text)


def strip_ruiwen_hometown(raw: bytes) -> str:
    html = raw.decode("gb18030", errors="ignore")
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", html)
    text = unescape(text)
    text = normalize_text(text)
    start = text.find("我冒了严寒，回到相隔二千余里")
    end = text.find("《故乡》简介", max(start, 0))
    if start == -1:
        start = text.find("深蓝的天空中挂着一轮金黄的圆月")
    if end == -1 or (start != -1 and end < start):
        end = text.find("一九二一年一月")
        if end != -1:
            end += len("一九二一年一月")
    if start != -1 and end != -1 and end > start:
        text = text[start:end]
    return normalize_text(text)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n\n".join(lines).strip()


def load_document(document: SeedDocument) -> str:
    try:
        raw = fetch_text(document.source_url)
        if document.parser == "wikisource_raw":
            text = strip_wikisource_raw(raw)
        elif document.parser == "ruiwen_hometown":
            text = strip_ruiwen_hometown(raw)
        else:
            raise ValueError(f"unknown parser: {document.parser}")
        if len(text) < 300:
            raise ValueError(f"cleaned text too short: {len(text)} chars")
        return text
    except Exception:
        if document.fallback_path is None:
            raise
        return (ROOT / document.fallback_path).read_text(encoding="utf-8")


def main() -> None:
    init_db()
    db = SessionLocal()
    service = KnowledgeService()
    try:
        for document in DOCUMENTS:
            body = load_document(document)
            content = (
                f"标题：{document.title}\n"
                f"作者：{document.author}\n"
                f"来源：{document.source_url}\n\n"
                f"{body}"
            )
            existing = db.query(KnowledgeDocument).filter(KnowledgeDocument.title == document.title).first()
            if existing:
                service.update_document(db, existing, document.title, content)
                action = "updated"
            else:
                service.create_document(db, document.title, content, source_type="real_text")
                action = "created"
            print(f"{action}: {document.title} chars={len(content)} source={document.source_url}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
