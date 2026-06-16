# Agent Knowledge Base Project Design

## 1. Project Goal

This project is designed for a selective Agent/RAG engineering task. It implements a lightweight knowledge base system that supports knowledge CRUD, text upload, semantic search, streaming search output, and an Agent-callable tool.

The target user flow is:

1. Upload or input knowledge documents, such as Zhu Ziqing's *Spring* and Lu Xun's *Hometown*.
2. Search natural language queries such as "spring", "young Runtu", or "child".
3. Retrieve the most relevant knowledge document and content snippets.
4. Let an Agent call the same retrieval capability through an MCP tool.

The project deliberately avoids using a fully packaged open-source RAG product. Instead, it implements the core retrieval pipeline directly so that the design, trade-offs, and limitations are visible and explainable.

## 2. Requirement Mapping

| Requirement | Design Response |
| --- | --- |
| Knowledge base CRUD with pagination | FastAPI REST APIs backed by SQLite and SQLAlchemy |
| Upload knowledge content | Support `.txt` upload and direct text input |
| Semantic retrieval | Use Chinese text embeddings plus cosine similarity |
| Query should return related knowledge bases | Retrieve chunks first, then aggregate scores back to documents |
| Streaming output | Use FastAPI `StreamingResponse` and Server-Sent Events |
| Agent-callable capability | Provide an MCP server with a `search_knowledge` tool |
| Basic error handling | Validate empty query, empty knowledge base, retrieval failure, and timeout |
| Submission readability | Provide README, design docs, examples, tests, and run scripts |

## 3. Final Technology Stack

### 3.1 Backend: Python + FastAPI

FastAPI is selected because it is lightweight, easy to run locally, and well suited for AI-oriented backend services. It provides clean request validation, automatic OpenAPI documentation, file upload support, and native streaming responses.

Alternative options considered:

- Flask: simpler, but weaker type validation and API documentation by default.
- Django: powerful, but too heavy for this task and unnecessary for a small RAG service.
- Node.js: usable, but the Python ecosystem is stronger for embedding models, vector computation, and RAG experiments.

Decision:

Use FastAPI as the backend API framework.

### 3.2 Database: SQLite

SQLite is selected because it requires no external service and is easy for reviewers to run locally. It is sufficient for document metadata, chunk text, embeddings, pagination, and small-scale retrieval.

Alternative options considered:

- PostgreSQL: production-grade, but requires external setup.
- Milvus or Qdrant: strong vector databases, but too heavy for a selection project.
- Chroma: convenient for demos, but hides some retrieval details and introduces another dependency layer.

Decision:

Use SQLite for local persistence. Store embeddings as JSON text or binary blobs, and compute similarity in Python.

### 3.3 ORM: SQLAlchemy

SQLAlchemy is selected to keep database access structured and maintainable. It also makes the schema clearer for reviewers than scattered raw SQL.

Decision:

Use SQLAlchemy models for `KnowledgeDocument` and `KnowledgeChunk`.

### 3.4 Embedding Model: BAAI/bge-small-zh-v1.5

The task contains Chinese literary examples. Pure keyword search cannot reliably solve semantic queries like "child" matching content about young Runtu. A Chinese embedding model is therefore required.

`BAAI/bge-small-zh-v1.5` is selected because:

- It supports Chinese semantic retrieval.
- It is relatively small and practical for local demos.
- It can be loaded through `sentence-transformers`.
- It keeps the system independent from paid external APIs.

Alternative options considered:

- OpenAI or cloud embedding APIs: good quality, but require API keys and network access.
- Larger local embedding models: potentially better quality, but slower and heavier for reviewers.
- Keyword-only retrieval: simple, but does not meet the semantic search requirement.

Decision:

Use `sentence-transformers` with `BAAI/bge-small-zh-v1.5`, while keeping the embedding service replaceable.

### 3.5 RAG Chunking Strategy: Paragraph-Aware Chunking

The example documents are literary texts, not structured technical manuals. Important semantic clues may span multiple sentences or paragraphs. A naive fixed-size split can cut through complete scenes and weaken retrieval quality.

The project uses paragraph-aware chunking:

1. Normalize text and remove excessive whitespace.
2. Split text by blank lines and natural paragraph boundaries.
3. Preserve complete paragraphs whenever possible.
4. Merge short paragraphs until the chunk reaches a target length.
5. Use overlap between neighboring chunks to preserve context.

Initial parameters:

| Parameter | Value | Reason |
| --- | --- | --- |
| Target chunk size | 400-800 Chinese characters | Large enough to preserve literary context, small enough for precise retrieval |
| Overlap | 80-150 Chinese characters or one short paragraph | Reduces boundary loss when key information sits near chunk edges |
| Minimum chunk size | About 120 characters | Avoids overly small fragments with weak semantics |
| Maximum chunk size | About 1,000 characters | Prevents chunks from becoming too broad and noisy |

Why this matters:

- Query "spring" should retrieve descriptive spring scenes from *Spring*.
- Query "young Runtu" should retrieve the Runtu scene from *Hometown*.
- Query "child" may not exactly appear as a keyword, so the chunk must preserve enough surrounding context for the embedding model to infer semantic relatedness.

Decision:

Implement paragraph-aware chunking rather than pure fixed-length splitting.

### 3.6 Retrieval Strategy: Hybrid Search

Vector search is good at semantic similarity, but it can miss exact names or rare phrases. Keyword search is strong for exact terms, but weak for paraphrases. The project combines both.

Retrieval uses:

1. Vector retrieval with cosine similarity.
2. Keyword retrieval with Chinese tokenization and BM25-like scoring.
3. Weighted score fusion.

Initial scoring formula:

```text
final_score = 0.75 * vector_score + 0.25 * keyword_score
```

Why this design is chosen:

- "spring" benefits from semantic retrieval.
- "young Runtu" benefits from exact keyword matching.
- "child" benefits mainly from semantic retrieval.
- Hybrid retrieval is more stable than either method alone for a small knowledge base demo.

Decision:

Use hybrid retrieval with vector similarity as the primary signal and keyword matching as a precision fallback.

### 3.7 Document-Level Aggregation

The system stores and retrieves chunks, but the user expects to find the relevant knowledge base document. Therefore, chunk-level matches must be aggregated back to documents.

Document score formula:

```text
document_score = 0.7 * max_chunk_score + 0.3 * average_top_3_chunk_score
```

Reasoning:

- `max_chunk_score` ensures that a document with one highly relevant passage can be found.
- `average_top_3_chunk_score` rewards documents with multiple relevant passages.
- This balances precise matching and document-level relevance.

Decision:

Return both the matched document and the most relevant chunks.

### 3.8 Streaming Response: SSE

The requirement says search results should appear progressively, similar to DeepSeek text generation. Since this project retrieves existing text instead of generating an answer with an LLM, streaming is implemented at the response layer.

The backend uses FastAPI `StreamingResponse` with Server-Sent Events.

The stream can emit:

1. Query validation status.
2. Retrieval progress.
3. Matched document title.
4. Matched snippets, character by character or sentence by sentence.
5. Completion event.

Decision:

Use SSE because it is simple, browser-friendly, and sufficient for one-way streaming search output.

### 3.9 Frontend: Native HTML + CSS + JavaScript

The frontend is intentionally simple. The project is judged mainly on knowledge base and Agent capability, not frontend framework complexity.

The UI should include:

- Knowledge list with pagination.
- Create, update, and delete operations.
- Text input import.
- `.txt` upload.
- Search box.
- Streaming result display.

Alternative options considered:

- React or Vue: more expressive, but add build steps and dependencies.
- Server-side templates: acceptable, but less flexible for streaming UI.

Decision:

Use native HTML, CSS, and JavaScript to reduce setup cost and keep the demo easy to run.

### 3.10 Agent Integration: MCP Server

The requirement asks to package the knowledge retrieval capability as either a skill or an MCP tool/server. MCP is selected because it is a standard tool-calling interface and clearly demonstrates that an Agent can invoke the retrieval capability.

Tool design:

```text
Tool name: search_knowledge

Input:
{
  "query": "spring related content",
  "top_k": 5
}

Output:
{
  "query": "spring related content",
  "results": [
    {
      "knowledge_id": 1,
      "title": "Zhu Ziqing - Spring",
      "score": 0.87,
      "content": "matched snippet"
    }
  ]
}
```

Error handling:

- Empty query: return a validation error.
- No knowledge documents: return a clear empty-state message.
- Retrieval failure: return a structured error.
- Timeout: return a timeout error with a readable message.

Decision:

Implement an MCP server and expose `search_knowledge` as the main Agent-callable tool.

## 4. Final Project Structure

```text
XXX-XXXUniversity-2026-06-09-Agent/
  README.md
  requirements.txt
  .env.example
  run_api.py
  run_mcp.py

  app/
    __init__.py
    main.py
    config.py
    database.py

    models/
      __init__.py
      knowledge.py
      chunk.py

    schemas/
      __init__.py
      knowledge.py
      search.py

    api/
      __init__.py
      knowledge_routes.py
      search_routes.py

    services/
      __init__.py
      knowledge_service.py
      chunk_service.py
      embedding_service.py
      keyword_service.py
      search_service.py
      stream_service.py

    mcp/
      __init__.py
      server.py
      tools.py

    static/
      index.html
      styles.css
      app.js

  data/
    knowledge.db
    uploads/
      .gitkeep

  examples/
    spring.txt
    hometown.txt
    api_demo.py
    mcp_client_demo.py
    eval_demo.py

  tests/
    test_chunk_service.py
    test_embedding_service.py
    test_keyword_service.py
    test_search_service.py
    test_knowledge_api.py

  docs/
    design.md
    api.md
    rag_strategy.md
    mcp_usage.md

  resume/
    XXX-resume.pdf
```

## 5. Core API Design

### Knowledge APIs

```text
GET    /api/knowledge?page=1&page_size=10
POST   /api/knowledge
GET    /api/knowledge/{id}
PUT    /api/knowledge/{id}
DELETE /api/knowledge/{id}
POST   /api/knowledge/upload
```

### Search APIs

```text
POST   /api/search
GET    /api/search/stream?query=spring&top_k=5
```

Example search response:

```json
{
  "query": "young Runtu",
  "results": [
    {
      "knowledge_id": 2,
      "title": "Lu Xun - Hometown",
      "score": 0.91,
      "chunks": [
        {
          "chunk_id": 12,
          "score": 0.91,
          "content": "matched text snippet"
        }
      ]
    }
  ]
}
```

## 6. Evaluation Plan

The project should include a small evaluation script to prove the key examples work.

Minimum evaluation cases:

| Query | Expected Result |
| --- | --- |
| 春天 | 朱自清《春》 |
| 少年闰土 | 鲁迅《故乡》 |
| 小孩子 | 鲁迅《故乡》 |

`examples/eval_demo.py` should:

1. Insert or load the two example documents.
2. Run the three queries.
3. Print top results and scores.
4. Mark whether expected documents appear in top 1 or top 2.

This is important because semantic retrieval should be demonstrated with evidence, not only described in the README.

## 7. Known Limitations and Future Improvements

This project intentionally chooses a lightweight local architecture. It has some limitations:

- SQLite vector search is acceptable for small data, but not for large-scale retrieval.
- Local embedding models may be slow on first load.
- Hybrid retrieval weights are heuristic and should be tuned with more evaluation data.
- The system retrieves relevant content but does not generate synthesized answers with citations.

Future upgrades:

- Replace SQLite vector computation with FAISS, Qdrant, Milvus, or pgvector.
- Add reranking with a cross-encoder model.
- Add LLM answer generation with cited snippets.
- Add user authentication and knowledge base permissions.
- Add batch import for PDF, Markdown, Word, or web pages.
- Add a formal retrieval evaluation dataset and metrics such as Recall@K and MRR.

## 8. Final Decision Summary

The final solution is:

```text
FastAPI + SQLite + SQLAlchemy
+ sentence-transformers / BAAI/bge-small-zh-v1.5
+ paragraph-aware chunking
+ hybrid vector and keyword retrieval
+ document-level aggregation
+ SSE streaming output
+ MCP server tool
+ native HTML/CSS/JavaScript frontend
```

This design is selected because it satisfies all required functions, remains easy to run locally, exposes the key RAG logic clearly, and demonstrates practical Agent tool integration without hiding the implementation behind a large existing RAG product.

## 9. Current Implementation Architecture

The implemented system is organized around two explicit pipelines: an ingestion pipeline and a retrieval pipeline.

### 9.1 Ingestion Pipeline

```text
User uploads txt or inputs text
  -> KnowledgeService creates or updates a knowledge document
  -> Text cleaning
  -> ChunkService performs paragraph-aware chunking
  -> EmbeddingService generates chunk embeddings
  -> SQLite stores knowledge_documents
  -> SQLite stores knowledge_chunks(content, embedding_json)
```

This pipeline is responsible only for turning raw knowledge content into retrievable document and chunk records.

### 9.2 Retrieval Pipeline

```text
Web Search API
Streaming Search API
MCP Tool search_knowledge
  -> all call the same SearchService
  -> SearchService generates query embedding
  -> Vector Search calculates cosine similarity
  -> KeywordService calculates jieba/BM25-like scores
  -> HybridRanker calculates final_score
  -> DocumentAggregator groups chunks by knowledge_id
  -> SearchLog writes query metadata to search_logs
```

The Web entrypoint and Agent entrypoint intentionally reuse the same `SearchService`, so both return consistent retrieval behavior.

### 9.3 MCP Server Responsibility

The MCP server is only a tool wrapper. It does not reimplement retrieval. The `search_knowledge` tool validates Agent input, calls `SearchService.search(..., entrypoint="mcp")`, handles timeout/errors, and returns an Agent-friendly structured result.

### 9.4 SQLite Tables

The implementation includes at least these tables:

- `knowledge_documents`
- `knowledge_chunks`
- `search_logs`
