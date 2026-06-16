from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/Users/wengchuangchuang/Documents/LLM-Learning/.conda/envs/smearglepaper/bin/python"


async def main() -> None:
    env = os.environ.copy()
    env.setdefault("FORCE_EMBEDDING_FALLBACK", "true")
    server = StdioServerParameters(
        command=PYTHON,
        args=[str(ROOT / "run_mcp.py")],
        env=env,
        cwd=str(ROOT),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            print("tools:", names)
            if "search_knowledge" not in names:
                raise SystemExit("search_knowledge tool not found")

            result = await session.call_tool(
                "search_knowledge",
                {
                    "query": "帮我查一下春天相关内容",
                    "top_k": 3,
                },
            )
            print("call_tool result:")
            for content in result.content:
                print(content)


if __name__ == "__main__":
    asyncio.run(main())
