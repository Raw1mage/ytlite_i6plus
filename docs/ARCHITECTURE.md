# 系統架構（繁體）

## 高層示意

```mermaid
graph TD
    User[使用者] -->|Safari WebClip / 瀏覽器| Client[iPhone 6 Plus]
    Client -->|HTTP(S)| Nginx[Nginx 反向代理 (選用)]
    Nginx -->|1214| API[FastAPI 中介層]
    API -->|1215| Invidious[Invidious 抓取]
    API -->|HTTPS| GAPI[YouTube Data API]
    Invidious --> DB[(PostgreSQL)]
    Invidious -->|HTTPS| YT[YouTube]
    API -->|HTML/JSON| Client
```

## 元件說明

### 1. 前端客戶端（iPhone 6 Plus / Safari）
- **技術**：HTML5 + Vanilla JS，無大型框架，行動優先設計。
- **功能**：全螢幕/迷你播放器、語音搜尋、動態導覽 Chips、訂閱內容同步顯示。
- **播放**：以 YouTube iframe 為核心，解決 Invidious 串流不穩問題。

### 2. 中介層（FastAPI，預設 1214）
- **核心邏輯**：
  - **OAuth2**：處理 Google 登入，Session 儲存於伺服器端文件系統 (`/app/data/sessions/`)。
  - **資料聚合**：實作「混合 Feed」，將訂閱頻道最新影片 (Invidious) 與隨機訂閱頻道 (YouTube API) 混合。
  - **使用者資料**：管理封鎖清單與自訂導覽設定，存於 `/app/data/users/`。
- **模板**：Jinja2 伺服器端渲染，直接產生適合舊版 iOS 的 HTML。

### 3. 抓取與資料層
- **Invidious**：主要的影片 Metadata 來源 (搜尋、頻道影片)，預設埠 1215。
- **YouTube Data API**：僅用於 OAuth 授權與同步訂閱清單 (因為 Invidious 處理私人訂閱較複雜)。
- **PostgreSQL**：Invidious 的資料庫，預設埠 1216。

### 4. 資料儲存結構 (`/app/data/`)
- `users/`：使用者設定檔 (e.g., `{uid}_blocked.json`, `{uid}_nav.json`)。
- `sessions/`：OAuth Session 快取檔。
- `client_secret.json`：Google OAuth 憑證。

## 數據流程
1. **首頁載入**：
   - 未登入：請求 Invidious 搜尋「台灣熱門」。
   - 已登入：並行請求 Invidious (針對訂閱頻道) 與 YouTube API (確認訂閱列表)，聚合後回傳混合 Feed。
2. **搜尋/導覽**：
   - 使用者點擊導覽 Chip → FastAPI 讀取 `users/{uid}_nav.json` 取得對應查詢詞 → 呼叫 Invidious Search API。
   - 回傳結果前，過濾掉 `users/{uid}_blocked.json` 中的頻道。
3. **播放**：
   - 前端點擊影片 → FastAPI 請求 Invidious 取得影片資訊 (Metadata) → 回傳頁面 (含 iframe)。
   - 若 Metadata 失敗，僅回傳 iframe 嘗試直接播放。

## 設計考量
- **運算轉移**：所有複雜邏輯 (聚合、過濾、模板) 皆在 Server 端完成，減輕 iPhone 6+負擔。
- **容錯性**：Invidious 服務不穩時，iframe 仍可獨立運作；圖片/標題載入失敗不應阻斷使用者操作。
- **隱私與個人化**：Token 與設定檔皆儲存於本地伺服器，不依賴瀏覽器 LocalStorage (除了基本的 UI 狀態)。
