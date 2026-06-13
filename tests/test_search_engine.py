from astrbot_plugin_search.core.search_engine import (
    SearchResult,
    WebSearchEngine,
    compact_html_preview,
    extract_page_text,
    _ddgs_region_for_query,
    _extract_weather_location,
    _looks_like_weather_query,
    _looks_like_spam_result,
)


def test_ddgs_result_conversion(monkeypatch):
    class FakeDDGS:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def text(self, query, **kwargs):
            assert query == "南昌 必吃 餐厅"
            assert kwargs["region"] == "cn-zh"
            return [
                {
                    "title": "南昌市美食 - Tripadvisor",
                    "href": "https://example.com/food",
                    "body": "餐廳推薦",
                },
                {
                    "title": "垃圾",
                    "href": "https://www.linkedin.com/jobs/spam",
                    "body": "约炮MM海选平台",
                },
            ]

    monkeypatch.setitem(__import__("sys").modules, "ddgs", type("M", (), {"DDGS": FakeDDGS}))
    engine = WebSearchEngine(user_agent="test")
    results = engine._ddgs_text("南昌 必吃 餐厅", timeout=3, limit=5)
    assert len(results) == 1
    assert results[0].title == "南昌市美食 - Tripadvisor"
    assert results[0].url == "https://example.com/food"
    assert results[0].source == "ddgs"


def test_search_locale_helpers_and_spam_filter():
    assert _ddgs_region_for_query("南昌 美食") == "cn-zh"
    assert _ddgs_region_for_query("Nanchang restaurants") == "us-en"
    assert _looks_like_spam_result("x", "https://www.linkedin.com/jobs/foo", "约炮")
    assert not _looks_like_spam_result("Tripadvisor", "https://example.com", "餐廳推薦")


def test_search_sync_uses_ddgs_and_dedupes(monkeypatch):
    engine = WebSearchEngine(user_agent="test")

    def fake_ddgs_text(query, timeout, limit):
        assert query == "南昌 美食"
        assert timeout == 3
        assert limit == 2
        return [
            SearchResult("A", "https://example.com/a", "one"),
            SearchResult("A duplicate", "https://example.com/a", "two"),
            SearchResult("B", "https://example.com/b", "three"),
        ]

    monkeypatch.setattr(engine, "_ddgs_text", fake_ddgs_text)
    results = engine.search_sync(" 南昌 美食 ", limit=2, timeout=3)
    assert [item["title"] for item in results] == ["A", "B"]


def test_search_result_snippet_is_trimmed():
    engine = WebSearchEngine(user_agent="test", max_snippet_chars=5)
    item = engine._result_to_dict(
        SearchResult(
            title="Example",
            url="https://example.com",
            snippet="123456789",
        )
    )
    assert item["snippet"] == "12345"


def test_extract_page_text_skips_script_and_style():
    html = """
    <html>
      <head><style>.x{color:red}</style><script>alert(1)</script></head>
      <body><h1>Hello</h1><p>Readable text</p></body>
    </html>
    """
    assert extract_page_text(html) == "Hello Readable text"


def test_compact_html_preview_keeps_useful_structure():
    html = '<article><h1>Title</h1><a href="https://example.com">Read</a></article>'
    preview = compact_html_preview(html)
    assert "<article>" in preview
    assert '<a href="https://example.com">' in preview
    assert "Title" in preview


def test_weather_query_detection_and_location_alias():
    assert _looks_like_weather_query("current weather Taipei")
    assert _looks_like_weather_query("台北今天天氣")
    assert _extract_weather_location("current weather Taipei") == "Taipei"
    assert _extract_weather_location("台北今天天氣") == "Taipei"
