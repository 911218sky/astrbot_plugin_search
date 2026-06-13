from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_LIMIT = 10
HTML_PREVIEW_ATTRS = {"href", "src", "alt", "title", "name", "content"}
WEATHER_TERMS = (
    "weather",
    "temperature",
    "forecast",
    "天氣",
    "天气",
    "氣溫",
    "气温",
    "預報",
    "预报",
)
WEATHER_STOP_WORDS = {
    "current",
    "now",
    "today",
    "tomorrow",
    "weather",
    "temperature",
    "forecast",
    "june",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
    "今日",
    "今天",
    "明天",
    "現在",
    "现在",
    "目前",
    "天氣",
    "天气",
    "氣溫",
    "气温",
    "幾度",
    "几度",
}
WEATHER_LOCATION_ALIASES = {
    "台北": "Taipei",
    "臺北": "Taipei",
    "台北市": "Taipei",
    "臺北市": "Taipei",
    "taipei": "Taipei",
    "東京": "Tokyo",
    "tokyo": "Tokyo",
    "大阪": "Osaka",
    "osaka": "Osaka",
    "香港": "Hong Kong",
    "hong kong": "Hong Kong",
    "首爾": "Seoul",
    "seoul": "Seoul",
    "紐約": "New York",
    "new york": "New York",
    "洛杉磯": "Los Angeles",
    "los angeles": "Los Angeles",
}
SPAM_TEXT_PATTERNS = (
    "约炮",
    "約炮",
    "海选平台",
    "援交",
    "博彩",
    "娱乐城",
)
SPAM_HOST_PARTS = (
    "linkedin.com/jobs/",
)


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "duckduckgo"


class WebSearchEngine:
    """Free web search with ddgs first, then direct free endpoint fallbacks."""

    def __init__(self, *, user_agent: str, max_snippet_chars: int = 500) -> None:
        self.user_agent = user_agent
        self.max_snippet_chars = max_snippet_chars

    async def search(
        self, query: str, *, limit: int = 5, timeout: float = 10.0
    ) -> list[dict[str, str]]:
        return await asyncio.to_thread(
            self.search_sync, query=query, limit=limit, timeout=timeout
        )

    async def enrich_results(
        self,
        results: list[dict[str, str]],
        *,
        timeout: float = 10.0,
        max_pages: int = 3,
        max_page_chars: int = 4000,
        include_html: bool = False,
        max_html_chars: int = 2000,
    ) -> list[dict[str, str]]:
        return await asyncio.to_thread(
            self.enrich_results_sync,
            results=results,
            timeout=timeout,
            max_pages=max_pages,
            max_page_chars=max_page_chars,
            include_html=include_html,
            max_html_chars=max_html_chars,
        )

    def search_sync(
        self, query: str, *, limit: int = 5, timeout: float = 10.0
    ) -> list[dict[str, str]]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("query must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        capped_limit = max(1, min(limit, MAX_LIMIT))
        results: list[SearchResult] = []
        seen: set[str] = set()

        if _looks_like_weather_query(cleaned_query):
            try:
                self._append_unique(
                    results,
                    seen,
                    self._weather_result(cleaned_query, timeout),
                    capped_limit,
                )
            except Exception:
                pass

        if len(results) < capped_limit:
            try:
                ddgs_results = self._ddgs_text(cleaned_query, timeout, capped_limit)
            except Exception:
                ddgs_results = []
            for result in ddgs_results:
                self._append_unique(results, seen, result, capped_limit)
                if len(results) >= capped_limit:
                    break

        try:
            instant_answer, related_topics = self._duckduckgo_instant_answer(
                cleaned_query, timeout
            )
        except Exception:
            instant_answer, related_topics = [], []

        for result in instant_answer:
            self._append_unique(results, seen, result, capped_limit)

        if len(results) < capped_limit:
            for result in self._duckduckgo_lite(cleaned_query, timeout):
                self._append_unique(results, seen, result, capped_limit)
                if len(results) >= capped_limit:
                    break

        if len(results) < capped_limit:
            try:
                bing_results = self._bing_rss(cleaned_query, timeout)
            except Exception:
                bing_results = []
            for result in bing_results:
                self._append_unique(results, seen, result, capped_limit)
                if len(results) >= capped_limit:
                    break

        if len(results) < capped_limit:
            for result in related_topics:
                self._append_unique(results, seen, result, capped_limit)
                if len(results) >= capped_limit:
                    break

        return [self._result_to_dict(result) for result in results[:capped_limit]]

    def enrich_results_sync(
        self,
        results: list[dict[str, str]],
        *,
        timeout: float = 10.0,
        max_pages: int = 3,
        max_page_chars: int = 4000,
        include_html: bool = False,
        max_html_chars: int = 2000,
    ) -> list[dict[str, str]]:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        capped_pages = max(0, min(int(max_pages), MAX_LIMIT))
        capped_text_chars = max(200, min(int(max_page_chars), 20000))
        capped_html_chars = max(0, min(int(max_html_chars), 10000))

        enriched: list[dict[str, str]] = [dict(item) for item in results]
        fetched = 0
        for item in enriched:
            if fetched >= capped_pages:
                break
            url = item.get("url", "")
            if not _is_fetchable_page_url(url):
                item["page_error"] = "unsupported or private URL"
                continue

            try:
                html = self._fetch_text(url, timeout)
            except Exception as exc:
                item["page_error"] = str(exc)
                fetched += 1
                continue

            page_text = extract_page_text(html)[:capped_text_chars].rstrip()
            if page_text:
                item["page_text"] = page_text
            if include_html and capped_html_chars:
                item["page_html"] = compact_html_preview(html)[:capped_html_chars].rstrip()
            fetched += 1
        return enriched

    def _append_unique(
        self,
        results: list[SearchResult],
        seen: set[str],
        result: SearchResult,
        limit: int,
    ) -> None:
        key = result.url or result.title
        if (
            not key
            or key in seen
            or len(results) >= limit
            or not _is_supported_result_url(result.url)
        ):
            return
        seen.add(key)
        results.append(result)

    def _duckduckgo_instant_answer(
        self, query: str, timeout: float
    ) -> tuple[list[SearchResult], list[SearchResult]]:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            }
        )
        data = self._fetch_json(f"https://api.duckduckgo.com/?{params}", timeout)

        instant_answer: list[SearchResult] = []
        related_topics: list[SearchResult] = []

        heading = _clean_text(str(data.get("Heading") or ""))
        abstract = _clean_text(str(data.get("AbstractText") or data.get("Abstract") or ""))
        abstract_url = _clean_url(str(data.get("AbstractURL") or ""))
        if heading and abstract_url:
            instant_answer.append(
                SearchResult(
                    title=heading,
                    url=abstract_url,
                    snippet=abstract,
                    source="duckduckgo_instant_answer",
                )
            )

        for topic in _flatten_related_topics(data.get("RelatedTopics", [])):
            title = _clean_text(str(topic.get("Text") or topic.get("FirstURL") or ""))
            url = _clean_url(str(topic.get("FirstURL") or ""))
            if title and url:
                related_topics.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=title,
                        source="duckduckgo_related_topic",
                    )
                )

        return instant_answer, related_topics

    def _duckduckgo_lite(self, query: str, timeout: float) -> Iterable[SearchResult]:
        params = urllib.parse.urlencode({"q": query})
        html = self._fetch_text(f"https://lite.duckduckgo.com/lite/?{params}", timeout)
        yield from parse_duckduckgo_lite(html)

    def _ddgs_text(
        self, query: str, timeout: float, limit: int
    ) -> list[SearchResult]:
        from ddgs import DDGS  # type: ignore[import-not-found]

        region = _ddgs_region_for_query(query)
        with DDGS(timeout=max(1, int(timeout))) as ddgs:
            raw_results = ddgs.text(
                query,
                region=region,
                safesearch="moderate",
                max_results=max(limit, 5),
            )

        results: list[SearchResult] = []
        for item in raw_results:
            title = _clean_text(str(item.get("title") or ""))
            url = _clean_url(str(item.get("href") or item.get("url") or ""))
            snippet = _clean_htmlish_text(str(item.get("body") or item.get("snippet") or ""))
            if title and url and not _looks_like_spam_result(title, url, snippet):
                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source="ddgs",
                    )
                )
        return results

    def _bing_rss(self, query: str, timeout: float) -> list[SearchResult]:
        locale = _bing_locale_for_query(query)
        params = urllib.parse.urlencode(
            {
                "q": query,
                "format": "rss",
                "mkt": locale["mkt"],
                "setlang": locale["setlang"],
                "cc": locale["cc"],
            }
        )
        xml_text = self._fetch_text(f"https://www.bing.com/search?{params}", timeout)
        return parse_bing_rss(xml_text)

    def _weather_result(self, query: str, timeout: float) -> SearchResult:
        location = _extract_weather_location(query)
        params = urllib.parse.urlencode({"format": "j1"})
        data = self._fetch_json(
            f"https://wttr.in/{urllib.parse.quote(location)}?{params}", timeout
        )
        current = _first_dict(data.get("current_condition"))
        area = _weather_area_name(data, location)
        desc = _first_value(current.get("weatherDesc")) or "unknown"
        temp_c = current.get("temp_C", "?")
        feels_c = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        wind_kmph = current.get("windspeedKmph", "?")
        precip_mm = current.get("precipMM", "?")
        observed = current.get("observation_time", "")
        snippet = (
            f"{area} current weather: {desc}, {temp_c}°C, feels like {feels_c}°C, "
            f"humidity {humidity}%, wind {wind_kmph} km/h, precipitation {precip_mm} mm."
        )
        if observed:
            snippet += f" Observation time: {observed} UTC."
        return SearchResult(
            title=f"Current weather for {area}",
            url=f"https://wttr.in/{urllib.parse.quote(location)}",
            snippet=snippet,
            source="wttr_in",
        )

    def _fetch_json(self, url: str, timeout: float) -> dict[str, Any]:
        text = self._fetch_text(url, timeout)
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("search provider returned non-object JSON")
        return data

    def _fetch_text(self, url: str, timeout: float) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"search provider response exceeded {MAX_RESPONSE_BYTES} bytes"
                )
            return body.decode(charset, errors="replace")

    def _result_to_dict(self, result: SearchResult) -> dict[str, str]:
        item = asdict(result)
        item["snippet"] = item["snippet"][: self.max_snippet_chars].rstrip()
        return item


def parse_duckduckgo_lite(html: str) -> list[SearchResult]:
    parser = _DuckDuckGoLiteParser()
    parser.feed(html)
    parser.close()
    return parser.results


def parse_bing_rss(xml_text: str) -> list[SearchResult]:
    root = ET.fromstring(xml_text)
    results: list[SearchResult] = []
    for item in root.findall("./channel/item"):
        title = _clean_text(item.findtext("title") or "")
        url = _clean_url(item.findtext("link") or "")
        snippet = _clean_htmlish_text(item.findtext("description") or "")
        if title and _is_supported_result_url(url):
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="bing_rss",
                )
            )
    return results


def extract_page_text(html: str) -> str:
    parser = _ReadableHTMLParser()
    parser.feed(html)
    parser.close()
    return _clean_text(" ".join(parser.text_parts))


def compact_html_preview(html: str) -> str:
    parser = _HTMLPreviewParser()
    parser.feed(html)
    parser.close()
    return "\n".join(line for line in parser.lines if line).strip()


def _looks_like_weather_query(query: str) -> bool:
    lowered = query.lower()
    return any(term in lowered for term in WEATHER_TERMS)


def _has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def _ddgs_region_for_query(query: str) -> str:
    return "cn-zh" if _has_cjk(query) else "us-en"


def _bing_locale_for_query(query: str) -> dict[str, str]:
    if _has_cjk(query):
        return {"mkt": "zh-CN", "setlang": "zh-CN", "cc": "CN"}
    return {"mkt": "en-US", "setlang": "en-US", "cc": "US"}


def _extract_weather_location(query: str) -> str:
    lowered = query.lower()
    for alias, location in WEATHER_LOCATION_ALIASES.items():
        if alias in lowered or alias in query:
            return location

    words = re.findall(r"[A-Za-z\u4e00-\u9fff]+", query)
    candidates = [
        word
        for word in words
        if word.lower() not in WEATHER_STOP_WORDS and not word.isdigit()
    ]
    if candidates:
        return " ".join(candidates[:3])
    return query


def _weather_area_name(data: dict[str, Any], fallback: str) -> str:
    nearest_area = _first_dict(data.get("nearest_area"))
    area_name = _first_value(nearest_area.get("areaName"))
    country = _first_value(nearest_area.get("country"))
    region = _first_value(nearest_area.get("region"))
    parts = [part for part in (area_name, region, country) if part]
    return ", ".join(parts) if parts else fallback


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    if isinstance(value, dict):
        return value
    return {}


def _first_value(value: Any) -> str:
    if isinstance(value, list) and value:
        item = value[0]
        if isinstance(item, dict):
            return _clean_text(str(item.get("value") or ""))
        return _clean_text(str(item))
    return _clean_text(str(value or ""))


class _DuckDuckGoLiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[SearchResult] = []
        self._in_link = False
        self._in_snippet = False
        self._current_url = ""
        self._current_title: list[str] = []
        self._pending_result: SearchResult | None = None
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        class_name = attrs_dict.get("class", "")

        if tag == "a" and "result-link" in class_name:
            self._finish_pending()
            self._in_link = True
            self._current_url = _clean_url(attrs_dict.get("href", ""))
            self._current_title = []
            return

        if tag == "td" and "result-snippet" in class_name and self._pending_result:
            self._in_snippet = True
            self._snippet_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._current_title.append(data)
        elif self._in_snippet:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_link:
            title = _clean_text(" ".join(self._current_title))
            if title and self._current_url and _is_supported_result_url(self._current_url):
                self._pending_result = SearchResult(
                    title=title,
                    url=self._current_url,
                    source="duckduckgo_lite",
                )
            self._in_link = False
            return

        if tag == "td" and self._in_snippet and self._pending_result:
            self._pending_result.snippet = _clean_text(" ".join(self._snippet_parts))
            self._finish_pending()
            self._in_snippet = False

    def close(self) -> None:
        super().close()
        self._finish_pending()

    def _finish_pending(self) -> None:
        if self._pending_result:
            self.results.append(self._pending_result)
            self._pending_result = None


class _ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            cleaned = _clean_text(data)
            if cleaned:
                self.text_parts.append(cleaned)


class _HTMLPreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        kept_attrs = []
        for key, value in attrs:
            if key in HTML_PREVIEW_ATTRS and value:
                kept_attrs.append(f'{key}="{_clean_text(value)}"')
        attrs_text = f" {' '.join(kept_attrs)}" if kept_attrs else ""
        self.lines.append(f"<{tag}{attrs_text}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if not self._skip_depth and tag in {
            "title",
            "h1",
            "h2",
            "h3",
            "p",
            "li",
            "a",
            "article",
            "section",
        }:
            self.lines.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            cleaned = _clean_text(data)
            if cleaned:
                self.lines.append(cleaned)


def _flatten_related_topics(value: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(value, list):
        return
    for item in value:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("Topics"), list):
            yield from _flatten_related_topics(item["Topics"])
        else:
            yield item


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _clean_htmlish_text(value: str) -> str:
    return _clean_text(re.sub(r"<[^>]+>", " ", value))


def _looks_like_spam_result(title: str, url: str, snippet: str) -> bool:
    combined = f"{title} {url} {snippet}".lower()
    if any(pattern.lower() in combined for pattern in SPAM_TEXT_PATTERNS):
        return True
    return any(part in combined for part in SPAM_HOST_PARTS)


def _clean_url(value: str) -> str:
    url = unescape(value).strip()
    if url.startswith("//duckduckgo.com/l/?"):
        url = f"https:{url}"
    elif url.startswith("/l/?"):
        url = f"https://duckduckgo.com{url}"

    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    redirect_target = query.get("uddg", [""])[0]
    if redirect_target:
        return redirect_target

    if url.startswith("//"):
        return f"https:{url}"
    return url


def _is_supported_result_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_fetchable_page_url(url: str) -> bool:
    if not _is_supported_result_url(url):
        return False
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").strip().lower()
    if not host or host in {"localhost", "localhost.localdomain"}:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast)
