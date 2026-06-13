from __future__ import annotations

import json
from dataclasses import field
from typing import Any

from pydantic.dataclasses import dataclass

from astrbot.api import logger
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext


def json_result(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@dataclass
class WebSearchTool(FunctionTool[AstrAgentContext]):
    __pydantic_config__ = {"arbitrary_types_allowed": True}

    plugin: Any = None
    name: str = "web_search"
    description: str = (
        "Search the web when current or external information is needed. "
        "Use this for latest facts, news, prices, schedules, unfamiliar topics, URLs, "
        "or when the user asks you to search. Do not use it for simple reasoning that "
        "does not require outside information."
    )
    parameters: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query. Use concise keywords, names, dates, and source hints.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
                "timeout": {
                    "type": "number",
                    "description": "HTTP timeout in seconds.",
                    "minimum": 1,
                    "maximum": 30,
                    "default": 10,
                },
                "include_pages": {
                    "type": "boolean",
                    "description": "Fetch readable page text from the top results when search snippets are not enough.",
                    "default": False,
                },
                "include_html": {
                    "type": "boolean",
                    "description": "Also include a compact HTML preview. Use only when HTML structure is needed.",
                    "default": False,
                },
                "fetch_pages": {
                    "type": "integer",
                    "description": "How many result pages to fetch when include_pages is true.",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 2,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        query: str,
        limit: int = 5,
        timeout: float = 10,
        include_pages: bool = False,
        include_html: bool = False,
        fetch_pages: int = 2,
    ) -> ToolExecResult:
        if self.plugin is None:
            return json_result(
                {
                    "query": query,
                    "status": "unavailable",
                    "message": "Search tool is not initialized.",
                    "user_message": "目前搜尋工具暫時不可用。",
                    "results": [],
                }
            )

        try:
            return json_result(
                await self.plugin.search(
                    query=query,
                    limit=limit,
                    timeout=timeout,
                    for_llm=True,
                    include_pages=include_pages,
                    include_html=include_html,
                    fetch_pages=fetch_pages,
                )
            )
        except Exception as exc:
            logger.warning(f"[Search] web_search failed: {exc}")
            return json_result(
                {
                    "query": query,
                    "status": "error",
                    "message": "Search failed before usable results were returned.",
                    "user_message": "目前搜尋來源暫時沒有回傳可用結果。",
                    "results": [],
                    "debug": str(exc),
                }
            )
