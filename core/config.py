from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_USER_AGENT = "astrbot-plugin-search/0.2.1 (+https://github.com/911218sky/astrbot_plugin_search)"


def _section(config: Any, key: str) -> dict[str, Any]:
    if hasattr(config, "get"):
        value = config.get(key, {}) or {}
        return value if isinstance(value, dict) else {}
    return {}


@dataclass(slots=True)
class SearchConfig:
    enable_llm_tool: bool = True
    enable_command: bool = True
    default_limit: int = 5
    timeout_seconds: float = 10.0
    max_query_chars: int = 300
    max_snippet_chars: int = 500
    enable_page_fetch: bool = True
    default_fetch_pages: int = 2
    max_page_chars: int = 4000
    max_html_chars: int = 2000
    user_agent: str = DEFAULT_USER_AGENT
    prompt_injection_guard: bool = True


class ConfigManager:
    def __init__(self, config: Any) -> None:
        raw = _section(config, "search")
        self.search = SearchConfig(
            enable_llm_tool=bool(raw.get("enable_llm_tool", True)),
            enable_command=bool(raw.get("enable_command", True)),
            default_limit=max(1, min(int(raw.get("default_limit", 5) or 5), 10)),
            timeout_seconds=max(1.0, min(float(raw.get("timeout_seconds", 10) or 10), 30.0)),
            max_query_chars=max(20, min(int(raw.get("max_query_chars", 300) or 300), 1000)),
            max_snippet_chars=max(
                80, min(int(raw.get("max_snippet_chars", 500) or 500), 2000)
            ),
            enable_page_fetch=bool(raw.get("enable_page_fetch", True)),
            default_fetch_pages=max(
                0, min(int(raw.get("default_fetch_pages", 2) or 2), 10)
            ),
            max_page_chars=max(
                200, min(int(raw.get("max_page_chars", 4000) or 4000), 20000)
            ),
            max_html_chars=max(
                0, min(int(raw.get("max_html_chars", 2000) or 2000), 10000)
            ),
            user_agent=str(raw.get("user_agent", "") or "").strip()
            or DEFAULT_USER_AGENT,
            prompt_injection_guard=bool(raw.get("prompt_injection_guard", True)),
        )
