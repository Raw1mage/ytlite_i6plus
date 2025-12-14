# 系統架構（繁體）

## 高層示意

```mermaid
graph TD
    User[使用者] -->|Safari WebClip / 瀏覽器| Client[iPhone 6 Plus]
    Client -->|HTTP(S)| Nginx[Nginx 反向代理 (選用)]
    Nginx -->|1214| API[FastAPI 中介層]
    API -->|1215| Invidious[Invidious 抓取]
    Invidious --> DB[(PostgreSQL)]
    API -->|HTML/JSON| Client
```

## 元件說明

### 1. 前端客戶端（iPhone 6 Plus / Safari）
- 以 WebClip 方式全螢幕呈現，UI 與搜尋關鍵字皆為繁體中文。
- 透過 iframe 播放影片，支援全螢幕與迷你播放器切換。

### 2. 中介層（FastAPI，預設 1214）
- 處理 OAuth2（Google 登入/訂閱），並將認證資料存於容器掛載的 `/app/data`。
- 將前端分類請求映射成 Invidious 搜尋（繁中關鍵字），並修正縮圖為外部可存取的 URL。
- 提供 Jinja2 模板與靜態資源，回傳 HTML/JSON 給前端。

### 3. 抓取與資料層
- **Invidious**：負責與 YouTube 互動並提供 API，預設埠 1215。
- **PostgreSQL**：Invidious 的資料庫，預設埠 1216。

### 4. 邊界與部署
- **Nginx（可選）**：統一 HTTPS 與反向代理，處理 `X-Forwarded-*` 標頭供 FastAPI 判斷回呼 URL。
- **環境變數**：`INVIDIOUS_API_URL`、`CLIENT_BASE_URL` 可覆寫內部位址與回呼網址。

## 數據流程
1. 使用者在 Safari 發出請求 → 送至 FastAPI（或經 Nginx 轉發）。
2. FastAPI 依分類組合繁中搜尋參數 → 呼叫 Invidious `/api/v1/search`。
3. FastAPI 修正縮圖 URL、回填 iframe 播放資訊 → 回傳給前端。
4. OAuth 登入時，FastAPI 以 Google OAuth Flow 取得 token，寫入 `/app/data/token.json`。

## 設計考量
- 舊裝置僅負責渲染與播放，運算集中於 PC/WSL。
- iframe 播放避免直抓串流造成 403/500；仍保留 metadata 嘗試但不阻斷播放。
- 以繁體中文為主要語系，搜尋關鍵字與分類預設為台灣熱門/新聞/直播等。
