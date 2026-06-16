from app.mcp.tools import search_knowledge_tool

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover
    raise RuntimeError("请先安装 MCP 依赖: pip install mcp") from exc


mcp = FastMCP("rag-agent-knowledge-base")


@mcp.tool()
def search_knowledge(query: str, top_k: int = 5):
    """Search the local RAG knowledge base and return relevant documents and snippets."""
    return search_knowledge_tool(query=query, top_k=top_k)


def main() -> None:
    mcp.run()
