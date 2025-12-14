# YT Lite v3（iPhone 6 Plus 版）

面向舊款 iPhone 6 Plus 的自架 YouTube 體驗。以 PC／WSL 上的 FastAPI 中介層與 Invidious 提供精簡內容，前端在手機 Safari（WebClip/PWA）播放，主要介面與資料均採繁體中文。

## 系統概要
- **前端客戶端**：iOS 12 Safari（WebClip/PWA），支援全螢幕與迷你播放。
- **中介層**：Python FastAPI，處理 OAuth、Invidious 代理與模板渲染（預設埠 `1214`）。
- **抓取層**：Invidious（預設埠 `1215`），資料庫 PostgreSQL（`1216`）。
- **代理**：Nginx 反向代理/HTTPS（選用）。
- **播放策略**：以 YouTube iframe 為主，避免直抓串流不穩。

## 快速啟動（開發）
1. 進入中介層專案：`cd ytlite_repo`
2. 建立虛擬環境並安裝依賴：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. 啟動 Invidious（可用 repo 內的 `docker-compose.yml`）：
   ```bash
   docker compose up -d
   ```
4. 啟動中介層（預設連到 `http://invidious:3000`；需要時可覆寫 `INVIDIOUS_API_URL`）：
   ```bash
   python3 -m uvicorn src.middleware.main:app --host 0.0.0.0 --port 1214 --reload
   ```
5. Safari 開啟 `http://<主機 IP>:1214`，加入主畫面即可全螢幕使用。

## 核心功能
- 繁體中文介面與搜尋關鍵字
- OAuth2 登入/登出與訂閱同步（需自備 `client_secret.json` 放在 `ytlite_repo/BUILD/data` 或 `src/middleware` 執行路徑）
- 影片清單與縮圖修正（外部可存取 URL）
- 全螢幕/迷你播放器，iframe 播放回退機制
- 分類快速切換（全部、新聞、直播、Podcast、觀看歷史）

## 目前風險與限制
- Invidious 偶有 metadata 失敗，標題/作者可能顯示「Loading...」，但播放不受影響。
- YouTube API 配額限制會影響訂閱同步。
- 舊款裝置效能有限，請避免同時執行重負載任務。

## 文件導覽
- 架構說明：`ARCHITECTURE.md`
- 開發計畫：`docs/PLAN.md`
- 進度摘要：`docs/PROGRESS.md`
- 除錯紀錄：`docs/DEBUGLOG.md`（完整細節見 `docs/HISTORY/DEBUG_LOG.md`）
- 團隊作業與紀律：`gemini.md`
