from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.mcp.tools import search_knowledge_tool


if __name__ == "__main__":
    print(search_knowledge_tool("帮我查一下春天相关内容", top_k=3))
