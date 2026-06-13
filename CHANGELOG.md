# 更新紀錄

## v0.2.1

- 精簡 README，移除注意事項段落。
- 移除設定頁的 HTTP User-Agent 欄位，改用內建預設值。
- 精簡設定頁，只保留常用開關與結果數設定。
- 同步版本號，方便確認 AstrBot Docker runtime 已載入新版插件。

## v0.2.0

- 修正未設定 `user_agent` 時可能拿到非字串預設值，導致搜尋 HTTP header 失敗的問題。
- 調整空結果與錯誤回傳格式，避免 AI 把 `No results`、`Need retry` 或內部錯誤原樣回給使用者。
- 加強提示與工具回傳內容，避免 `Search failed`、`Need search`、重試文字外露給使用者。
- 改用 `ddgs` 社群搜尋庫作為主要搜尋來源，移除手寫 DuckDuckGo/Bing 搜尋頁解析。
- 搜尋回覆預設不再貼網址；網址只保留給工具內部參考，除非使用者明確要求。
- 新增天氣查詢 fallback，可回答 `Taipei weather`、`台北天氣` 這類問題。
- 新增 `include_pages`，AI 需要時可以讀取搜尋結果網頁文字。
- 新增 `include_html`，必要時可回傳少量 HTML 預覽。
- 新增頁面抓取長度與頁數設定，避免 token 消耗失控。
- README 改成簡單易懂的使用說明。

## v0.1.0

- 新增 `/search <關鍵字>` 指令。
- 新增 AI 可自行呼叫的 `web_search` 工具。
- 使用免費搜尋來源，不需要 API key。
