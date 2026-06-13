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
- `enable_page_fetch`：是否允許 AI 抓搜尋結果頁面內容。
- `default_fetch_pages`：最多抓幾個搜尋結果頁面。

## Token 消耗

只看搜尋摘要最省 token。  
開啟 `include_pages` 會把網頁文字交給 AI，看得比較多，但 token 也會增加。  
開啟 `include_html` 更重，建議只有真的需要分析網頁結構時才用。

## 授權與來源

本專案使用 AGPL-3.0 授權。
