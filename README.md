# YT Lite

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
- **繁體中文介面**：針對台灣使用者優化的搜尋關鍵字與介面。
- **OAuth2 登入與訂閱同步**：支援 Google 帳號登入，自動同步 YouTube 訂閱頻道至側邊欄 (Drawer)。
- **混合訂閱 Feed**：首頁「全部」分頁會自動混合訂閱頻道的最新影片。
- **高度客製化**：
    - **自訂導覽 Chips**：可於「導覽管理」頁面新增、編輯首頁上方的快速分類按鈕。
    - **封鎖管理**：可封鎖不想看到的頻道，過濾首頁與搜尋結果。
- **播放體驗**：全螢幕/迷你播放器，採用 YouTube iframe 確保播放穩定性，支援 iOS 背景播放（視系統版本而定）。
- **輕量化架構**：針對舊款 iPhone 6 Plus (iOS 12) 優化，減少不必要的 JS 運算。

## 文件維護指南
- **計畫/進度**：功能開發前後請更新 `docs/PLAN.md` 與 `docs/PROGRESS.md`。
- **除錯紀錄**：遇到問題請記錄於 `docs/DEBUGLOG.md`，長篇分析放入 `docs/HISTORY/`。
- **架構變更**：若有新增服務或改變流程，請同步更新 `ARCHITECTURE.md`。

## 目前風險與限制
- **Invidious 依賴**：Metadata（標題/圖片）依賴 Invidious 實例，若實例不穩可能導致部分資訊載入失敗（顯示 Loading），但不影響 iframe 播放。
- **YouTube API 配額**：訂閱同步使用官方 API，受限於每日配額，目前設有快取機制。
- **舊機效能**：雖然已優化，但在舊裝置上仍應避免快速頻繁切換頁面。

## 文件導覽
- 架構說明：`ARCHITECTURE.md`
- 開發計畫：`docs/PLAN.md`
- 進度摘要：`docs/PROGRESS.md`
- 除錯紀錄：`docs/DEBUGLOG.md`
- 團隊作業：`gemini.md`
