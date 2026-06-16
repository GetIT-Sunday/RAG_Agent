# 项目设计说明

本项目实现一个轻量 RAG 知识库系统，并把检索能力封装成 MCP tool，供 Agent 调用。系统不是简单把 Web API 和 MCP 各写一套逻辑，而是把能力拆成两条核心 pipeline，并让 Web 端和 Agent 端复用同一个检索服务。

核心决策：FastAPI + SQLite + SQLAlchemy + bge-small-zh-v1.5/fallback embedding + 段落感知切分 + hybrid search + 文档级聚合 + SSE + MCP。

## 架构总览

```text
Web 前端/API 入口
  -> Knowledge API / Search API / Streaming Search API

Agent 入口
  -> MCP Server
  -> search_knowledge tool

两类入口最终都复用:
  -> KnowledgeService
  -> SearchService
  -> SQLite
```

MCP Server 只做工具层封装，不重复实现检索逻辑。这样可以保证 Web 查询和 Agent 查询的结果一致，也更容易维护。

## 入库链路 Ingestion Pipeline

```text
用户上传 txt 或直接输入文本
  -> KnowledgeService 创建/更新知识库
  -> 文本清洗
  -> ChunkService 做 paragraph-aware chunking
  -> EmbeddingService 生成 chunk embedding
  -> 保存 knowledge_documents
  -> 保存 knowledge_chunks(content, embedding_json)
```

入库链路选择 paragraph-aware chunking，是因为《春》《故乡》这类文学文本依赖段落和场景上下文。如果只按固定字符数硬切，容易切断“少年闰土”“童年伙伴”等语义场景。

## 查询链路 Retrieval Pipeline

```text
Web Search API ─────────────┐
Streaming Search API ───────┼──> SearchService
MCP Tool search_knowledge ──┘

SearchService
  -> 生成 query embedding
  -> Vector Search 计算 cosine similarity
  -> KeywordService 计算 jieba/BM25-like 分数
  -> HybridRanker 计算 final_score
  -> DocumentAggregator 按 knowledge_id 聚合结果
  -> 写入 search_logs
```

查询链路使用 hybrid search，是因为向量检索适合“春天”“小孩子”这类语义查询，关键词检索适合“少年闰土”这类精确短语。两者结合比单一策略更稳。

## SQLite 表结构

- `knowledge_documents`：知识库文档，保存标题、原文、来源类型、创建/更新时间。
- `knowledge_chunks`：文档片段，保存 `document_id`、`chunk_index`、`content`、`embedding_json`、字符数。
- `search_logs`：查询日志，保存 query、入口类型、top_k、结果数量、embedding backend、耗时和错误信息。

## Agent 开发体现

本项目选择 MCP tool / MCP server，而不是 skill。Agent 可调用的工具是：

```text
search_knowledge(query: str, top_k: int = 5)
```

该工具内部调用同一个 `SearchService`，返回 Agent-friendly 的结构化结果，包括 query、相关知识库标题、分数和片段。错误处理覆盖 query 为空、知识库为空、检索失败和工具调用超时。
