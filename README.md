# RagAgent 知识库 + MCP 工具

这是一个面向 Agent/RAG 选拔项目的轻量知识库系统，支持知识库增删改查、分页、`.txt` 上传、直接输入文本、中文语义检索、SSE 流式返回，并将检索能力封装为 MCP tool，供 Agent 调用。

## 技术栈

- Python 3.9+
- FastAPI + SQLite + SQLAlchemy
- sentence-transformers + `BAAI/bge-small-zh-v1.5`
- jieba + BM25-like keyword retrieval
- MCP Server
- 原生 HTML/CSS/JavaScript

## 为什么这样设计

本项目没有直接套用完整 RAG 产品，而是自己实现核心链路：文本清洗、段落感知切分、embedding、hybrid retrieval、文档级聚合和流式输出。这样更容易说明每个工程选择的原因，也便于评审看到可运行、可解释的实现。

主 embedding 模型使用 `BAAI/bge-small-zh-v1.5`，用于中文语义检索。默认启动时优先读取本地缓存模型；如果没有缓存，会自动降级到本地哈希向量 + 中文查询扩展，保证 CRUD、上传、检索和 MCP demo 仍可跑通。若需要正式语义 embedding，请额外安装 `requirements-embedding.txt`，并在需要首次联网下载模型时设置 `ALLOW_MODEL_DOWNLOAD=true` 后再启动。

## 系统架构

系统拆成两条核心链路：入库链路和查询链路。Web 端和 Agent 端是两个入口，但二者复用同一套 `SearchService`，MCP Server 只负责工具层封装，不重复实现检索逻辑。

```text
Ingestion Pipeline

用户上传 txt / 直接输入文本
  -> FastAPI Knowledge API
  -> KnowledgeService 创建或更新知识库
  -> 文本清洗
  -> ChunkService paragraph-aware chunking
  -> EmbeddingService 生成 chunk embedding
  -> SQLite 保存 knowledge_documents
  -> SQLite 保存 knowledge_chunks(content, embedding_json)
```

```text
Retrieval Pipeline

Web Search API ─────────────┐
Streaming Search API ───────┼──> SearchService
MCP Tool search_knowledge ──┘       |
                                    v
                            query embedding
                                    |
                    ┌───────────────┴───────────────┐
                    v                               v
              Vector Search                  KeywordService
          cosine similarity                 jieba + BM25-like
                    └───────────────┬───────────────┘
                                    v
                              HybridRanker
                         final_score = vector + keyword
                                    |
                                    v
                            DocumentAggregator
                     按 knowledge_id 聚合成知识库结果
                                    |
                                    v
                         SQLite 写入 search_logs
```

```text
Web 入口
  浏览器页面 -> FastAPI -> SearchService -> SQLite

Agent 入口
  Agent -> MCP Server -> search_knowledge tool -> SearchService -> SQLite
```

SQLite 至少包含三张表：

- `knowledge_documents`：知识库文档元信息和原文
- `knowledge_chunks`：切分后的片段、chunk 序号、`embedding_json`
- `search_logs`：查询入口、query、结果数量、耗时和错误信息

## 快速开始

```bash
cd /Users/wengchuangchuang/Documents/RagAgent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 可选：安装正式 embedding 模型依赖，包较大，网络差时可跳过
# pip install -r requirements-embedding.txt
python run_api.py
```

打开浏览器访问：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

## API 示例

创建知识库：

```bash
curl -X POST http://127.0.0.1:8000/api/knowledge \
  -H 'Content-Type: application/json' \
  -d '{"title":"朱自清《春》","content":"盼望着，盼望着，东风来了，春天的脚步近了。"}'
```

搜索：

```bash
curl -X POST http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"春天","top_k":5}'
```

流式搜索：

```bash
curl -N 'http://127.0.0.1:8000/api/search/stream?query=少年闰土&top_k=5'
```

## MCP Server

本项目实现的是一个实际可接入 Agent 的 MCP server，不是只在 Python 内部调用的 demo。MCP server 入口是：

```text
run_mcp.py
```

它暴露一个工具：

```text
search_knowledge(query: str, top_k: int = 5)
```

MCP Server 只做工具层封装，内部调用同一套 `SearchService`，不重复实现检索逻辑。

启动 MCP server：

```bash
FORCE_EMBEDDING_FALLBACK=true \
/Users/wengchuangchuang/Documents/LLM-Learning/.conda/envs/smearglepaper/bin/python run_mcp.py
```

### Agent 配置

支持 MCP 的 Agent 可以使用 `mcp_config.example.json` 中的配置：

```json
{
  "mcpServers": {
    "ragagent-knowledge-base": {
      "command": "/Users/wengchuangchuang/Documents/LLM-Learning/.conda/envs/smearglepaper/bin/python",
      "args": [
        "/Users/wengchuangchuang/Documents/RagAgent/run_mcp.py"
      ],
      "env": {
        "FORCE_EMBEDDING_FALLBACK": "true"
      }
    }
  }
}
```

Agent 连接后可以调用：

```json
{
  "query": "帮我查一下春天相关内容",
  "top_k": 5
}
```

返回内容包括 query、相关知识库标题、分数、相关片段，适合 Agent 继续整理成自然语言回答。默认工具超时为 90 秒，用于覆盖首次模型加载时间；后续调用通常会更快。

如果知识库中没有足够相关的内容，MCP 工具不会强行返回弱相关文档，而是返回：

```json
{
  "ok": true,
  "answer": "不知道，知识库中未找到与该问题足够相关的内容。",
  "fallback_to_base_model": true,
  "suggested_next_action": "answer_with_base_model",
  "agent_instruction": "知识库未命中。请明确告诉用户该问题未在知识库中找到相关内容；如果用户需要答案，请基于你的基础模型能力继续回答，并说明该回答不是来自知识库。",
  "results": []
}
```

这时 Agent 可以基于自己的基础模型回答，并说明该回答不是来自知识库检索结果。

推荐在 Agent 中这样提问以验证 fallback：

```text
请先调用 search_knowledge 查询“如何配置 Kubernetes Ingress”。
如果工具返回 fallback_to_base_model=true，请继续基于你的基础模型回答，并说明该回答不是来自知识库。
```

### MCP 协议级测试

使用真正的 MCP stdio client 启动本地 MCP server、列出工具并调用 `search_knowledge`：

```bash
FORCE_EMBEDDING_FALLBACK=true \
/Users/wengchuangchuang/Documents/LLM-Learning/.conda/envs/smearglepaper/bin/python examples/mcp_protocol_test.py
```

这比 `examples/mcp_client_demo.py` 更接近真实 Agent 调用，因为它走的是 MCP 协议而不是直接调用 Python 函数。

## 示例评测

```bash
python examples/eval_demo.py
```

评测目标：

- `春天` -> 朱自清《春》
- `少年闰土` -> 鲁迅《故乡》
- `小孩子` -> 鲁迅《故乡》

## 真实语料入库

可以运行脚本抓取公开文本并写入 SQLite：

```bash
FORCE_EMBEDDING_FALLBACK=true \
python examples/seed_real_documents.py
```

当前脚本会导入：

- 朱自清《春》：维基文库
- 鲁迅《故乡》：瑞文网鲁迅公版原文页面
- 鲁迅《从百草园到三味书屋》：维基文库
- 鲁迅《社戏》：维基文库

入库后可以测试：

```text
春天 -> 朱自清《春》
少年闰土 -> 鲁迅《故乡》
小孩子 -> 鲁迅《故乡》
百草园里的童年趣事 -> 鲁迅《从百草园到三味书屋》
看社戏的小伙伴 -> 鲁迅《社戏》
故乡的变化和希望 -> 鲁迅《故乡》
```

## 提交打包建议

最终提交时将项目目录改名为：

```text
XXX(名字)-XXX大学-2026-06-09-Agent
```

并将最新简历放入 `resume/` 后压缩发送。
