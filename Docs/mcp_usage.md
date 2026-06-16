# MCP Server 使用说明

本项目选择实现 MCP tool / MCP server，而不是 skill。它是一个可被支持 MCP 的 Agent 连接和调用的小型 MCP 项目。

MCP Server 只做 Agent 工具层封装，不重复实现检索逻辑。

```text
Agent
  -> MCP Server
  -> search_knowledge tool
  -> SearchService
  -> SQLite knowledge_documents / knowledge_chunks
  -> Agent-friendly structured result
```

## 启动

```bash
FORCE_EMBEDDING_FALLBACK=true \
/Users/wengchuangchuang/Documents/LLM-Learning/.conda/envs/smearglepaper/bin/python run_mcp.py
```

## 工具

```text
search_knowledge(query: str, top_k: int = 5)
```

工具内部调用 `SearchService.search(..., entrypoint="mcp")`，因此它和 Web Search API、Streaming Search API 复用同一套 Retrieval Pipeline。

## Agent 配置

见项目根目录：

```text
mcp_config.example.json
```

配置内容：

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

## MCP 协议级测试

运行：

```bash
FORCE_EMBEDDING_FALLBACK=true \
/Users/wengchuangchuang/Documents/LLM-Learning/.conda/envs/smearglepaper/bin/python examples/mcp_protocol_test.py
```

该脚本会通过 MCP stdio client 启动本地 MCP server，调用 `list_tools`，确认存在 `search_knowledge`，然后通过 `call_tool` 调用它。

## 返回结构

```json
{
  "ok": true,
  "query": "帮我查一下春天相关内容",
  "embedding_backend": "fallback-hash",
  "results": [
    {
      "knowledge_id": 1,
      "title": "朱自清《春》",
      "score": 0.25,
      "chunks": [
        {
          "chunk_id": 1,
          "score": 0.25,
          "vector_score": 0.0,
          "keyword_score": 1.0,
          "content": "相关片段"
        }
      ]
    }
  ]
}
```

如果知识库没有足够相关结果，工具返回：

```json
{
  "ok": true,
  "query": "如何配置 Kubernetes Ingress",
  "answer": "不知道，知识库中未找到与该问题足够相关的内容。",
  "fallback_to_base_model": true,
  "suggested_next_action": "answer_with_base_model",
  "agent_instruction": "知识库未命中。请明确告诉用户该问题未在知识库中找到相关内容；如果用户需要答案，请基于你的基础模型能力继续回答，并说明该回答不是来自知识库。",
  "results": []
}
```

这表示 RAG 知识库不应编造答案。Agent 可以继续使用自身基础模型回答，并向用户说明该部分不是知识库检索结果。

错误处理：

- query 为空：返回结构化错误
- 知识库为空：返回空知识库提示
- 检索失败：返回失败原因
- 超时：返回工具调用超时
