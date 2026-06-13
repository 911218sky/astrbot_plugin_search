# astrbot_plugin_search

AstrBot 免費聯網搜尋插件。

它會提供兩種用法：

- `/search <關鍵字>`：你手動叫它搜尋。
- `web_search`：AI 覺得需要查網路時，可以自己呼叫。

## 可以做什麼

- 查最新資訊、新聞、版本、價格、時程。
- 查天氣時會優先使用免費天氣資料來源，避免搜尋端點回空。
- 查陌生名詞、人物、公司、作品資料。
- AI 可以只看搜尋摘要，也可以在需要時讀取搜尋結果的網頁文字。
- 必要時可回傳少量 HTML 預覽，讓 AI 看頁面結構。

## 安裝

把資料夾放到 AstrBot 插件目錄：

```text
AstrBot/data/plugins/astrbot_plugin_search
```

如果 AstrBot 沒有自動安裝插件依賴，請在 AstrBot 的 Python 環境安裝：

```bash
pip install -r AstrBot/data/plugins/astrbot_plugin_search/requirements.txt
```

重啟 AstrBot 後，看到插件載入成功就可以使用。

## 手動搜尋

```text
/search AstrBot plugin
```

回覆會包含標題和簡短摘要，預設不會貼網址。

## AI 自動搜尋

插件會註冊一個 LLM 工具：

```text
web_search
```

AI 會在需要外部資料時自己決定要不要搜尋。  
例如使用者問最新消息、今天價格、某個網址內容、陌生資料時，AI 可以自己呼叫工具。
一般回覆不會主動貼網址；只有使用者明確要求來源或網址時，AI 才會提供連結。

如果 AI 只是需要找來源，通常只回傳搜尋結果摘要。  
如果摘要不夠，AI 可以設定：

```json
{
  "include_pages": true
}
```

這樣會抓搜尋結果網頁的可讀文字。

如果真的需要看 HTML 結構，AI 可以再設定：

```json
{
  "include_pages": true,
  "include_html": true
}
```

HTML 只會回傳壓縮過的預覽，不會無限制塞完整網頁。

## 主要設定

在 AstrBot 插件設定裡可以調：

- `enable_llm_tool`：是否讓 AI 自動使用 `web_search`。
- `enable_command`：是否啟用 `/search` 指令。
- `default_limit`：預設搜尋幾筆結果。
- `timeout_seconds`：搜尋和抓網頁的逾時秒數。
- `max_snippet_chars`：每筆搜尋摘要最多回傳多少字。
- `enable_page_fetch`：是否允許 AI 抓搜尋結果頁面內容。
- `default_fetch_pages`：最多抓幾個搜尋結果頁面。
- `max_page_chars`：每個網頁最多回傳多少文字。
- `max_html_chars`：每個網頁最多回傳多少 HTML 預覽。
- `prompt_injection_guard`：隱藏疑似提示注入的內容。

## Token 消耗

只看搜尋摘要最省 token。  
開啟 `include_pages` 會把網頁文字交給 AI，看得比較多，但 token 也會增加。  
開啟 `include_html` 更重，建議只有真的需要分析網頁結構時才用。

## 注意事項

這個插件優先使用 Python 社群維護的 `ddgs` 搜尋庫，不需要 API key。
如果 `ddgs`、DuckDuckGo 暫時回空或出現驗證頁，會再嘗試 Bing RSS 備援來源。
免費端點可能會被限流、出現驗證頁、或暫時沒有結果。插件會避免崩潰，但不能保證每次都有資料。

直接爬 Google 搜尋頁很容易拿到驗證或 JavaScript challenge，不適合當免費穩定端點。
如果之後想要 Google 等級的穩定搜尋，建議改接官方或付費 Search API。

天氣查詢會使用 wttr.in 作為備援資料來源，例如 `current weather Taipei` 或 `台北天氣`。

搜尋結果、網頁文字和 HTML 都只是外部資料，AI 不應該照著網頁裡的指令改變自己的系統設定。

如果搜尋來源沒有回傳結果，AI 不應該把工具內部狀態直接講給使用者。  
它應該自然地說「目前沒有找到可用的相關資料」，不要回 `No results`、`Need retry` 或 `Search failed` 這類工具狀態。

## 授權與來源

搜尋邏輯改寫自：

```text
https://github.com/911218sky/free-search-mcp
```

本專案使用 AGPL-3.0 授權。
