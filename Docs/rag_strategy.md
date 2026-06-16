# RAG 策略说明

## Ingestion Pipeline

入库链路负责把用户输入的知识内容变成可检索的结构化数据：

```text
txt 上传 / 直接输入文本
  -> KnowledgeService
  -> 文本清洗
  -> ChunkService
  -> EmbeddingService
  -> SQLite documents + chunks + embedding_json
```

## Chunking

文学文本依赖段落和场景上下文，因此 `ChunkService` 使用段落感知切分，而不是简单按固定字符数硬切。

默认参数：

- target chunk: 400-800 中文字符
- overlap: 80-150 中文字符或一个短段落
- max chunk: 1000 中文字符

## Retrieval

查询链路由 `SearchService` 统一编排，Web Search API、Streaming Search API 和 MCP Tool 都调用它：

```text
query
  -> query embedding
  -> Vector Search
  -> KeywordService
  -> HybridRanker
  -> DocumentAggregator
  -> search_logs
```

系统同时使用向量检索和关键词检索：

```text
final_score = 0.75 * vector_score + 0.25 * keyword_score
```

原因：

- `春天` 这类查询依赖语义召回。
- `少年闰土` 这类查询依赖精确词召回。
- `小孩子` 这类查询需要语义模型或查询扩展理解童年、少年、孩子等相关概念。

## Document Aggregation

`HybridRanker` 得到 chunk 级别分数后，`DocumentAggregator` 会把 chunk 命中结果聚合回知识库文档：

```text
document_score = 0.7 * max_chunk_score + 0.3 * average_top_3_chunk_score
```

这样用户和 Agent 都拿到“相关知识库 + 相关片段”，而不是孤立 chunk。
