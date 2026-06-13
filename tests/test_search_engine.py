from astrbot_plugin_search.core.search_engine import (
    WebSearchEngine,
    compact_html_preview,
    extract_page_text,
    parse_duckduckgo_lite,
)


def test_parse_duckduckgo_lite_result():
    html = """
    <a class="result-link" href="/l/?uddg=https%3A%2F%2Fexample.com">Example</a>
    <td class="result-snippet"> Example snippet </td>
    """
    results = parse_duckduckgo_lite(html)
    assert len(results) == 1
    assert results[0].title == "Example"
    assert results[0].url == "https://example.com"
    assert results[0].snippet == "Example snippet"


def test_search_result_snippet_is_trimmed():
    engine = WebSearchEngine(user_agent="test", max_snippet_chars=5)
    item = engine._result_to_dict(
        parse_duckduckgo_lite(
            """
            <a class="result-link" href="https://example.com">Example</a>
            <td class="result-snippet">123456789</td>
            """
        )[0]
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
