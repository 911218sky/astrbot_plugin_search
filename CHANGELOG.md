# 更新紀錄

## v0.2.0

- 調整空結果與錯誤回傳格式，避免 AI 把 `No results`、`Need retry` 或內部錯誤原樣回給使用者。
- 新增天氣查詢 fallback，DuckDuckGo 回空時仍可回答 `Taipei weather`、`台北天氣` 這類問題。
- 新增 `include_pages`，AI 需要時可以讀取搜尋結果網頁文字。
- 新增 `include_html`，必要時可回傳少量 HTML 預覽。
- 新增頁面抓取長度與頁數設定，避免 token 消耗失控。
- README 改成簡單易懂的使用說明。

## v0.1.0

- 新增 `/search <關鍵字>` 指令。
- 新增 AI 可自行呼叫的 `web_search` 工具。
- 使用免費 DuckDuckGo 搜尋端點，不需要 API key。
