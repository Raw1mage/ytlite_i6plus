# YT Lite 系統架構分析 (Architecture Sync)

## 1. 系統高層拓墣 (High-Level Topology)

YT Lite 採用中介代理架構，透過本地的中間件負責組裝前端所需要的資料。主要目的在減輕舊設備（如 iPhone 6 Plus、iOS 12 Safari WebClip）的運算壓力與網路請求數，並將複雜的封鎖、訂閱過濾與快取等資源密集型作業全數轉移到伺服器層。

```mermaid
graph TD
    User["使用者 (iPhone 6+ / Safari)"] -->|HTTP(S) Port 1214| API["FastAPI 中介層 (Container: ytlite)"]
    
    subgraph yt-lite 核心中介層
        API -->|Jinja2 Templates| UI["伺服器端渲染 (SSR HTML/JS)"]
        API -->|背景佇列: queue_manager.py| YTDLP["yt-dlp 快取/下載 (downloader.py)"]
        YTDLP -->|儲存 .mp3/.mp4| FS_Data["本機檔案系統 (/app/data/)<br/>(Cache & Downloads)"]
        API -->|讀寫 JSON| FS_User["使用者設定 (/data/users)<br/>Session (/data/sessions)"]
    end

    subgraph 遠端或外部代理層
        API -->|Metadata / Search (Port: 1215)| Invidious["Invidious 引擎 (Container: ytlite-engine)"]
        Invidious --> IDB[("PostgreSQL (Container: ytlite-postgres)")]
        Invidious -->|Proxy Request| YT["YouTube Servers"]
        API -->|OAuth2 (認證 / 訂閱列表)| GAPI["Google API / YouTube Data API"]
        YTDLP -->|媒體串流下載| YT
    end
```

---

## 2. 核心元件與職責劃分

### 2.1. 中介層 API (FastAPI)
- **進入點**：`webbox/src/middleware/main.py`
- **職責**：
  - **靜態資源與模版**：使用 `Jinja2Templates` 直接將畫面輸出給老裝置，減少 SPA (Single Page Application) 的 JS 解析壓力。路由包含 `/` (首頁)、`/watch`、`/playlist`，以及新功能 `/downloads`。
  - **資料聚合 (Data Aggregation)**：實作混合訂閱邏輯。將 YouTube API 返回的私人訂閱清單，加上 Invidious 查詢到的「台灣熱門」與搜尋結果混合。
  - **授權 (Authentication)**：透過 `client_secret.json` 完成 Google OAuth2 流程。Session 採無狀態 cookie，金鑰狀態寫死於本地路徑 `/app/data/sessions/`，避免外部資料庫依賴。
  - **過濾機制 (Blocklist)**：根據 `/app/data/users/{uid}_blocked.json`，在伺服器端直接拿掉不想顯示的頻道影片。

### 2.2. 非同步快取與下載佇列 (`queue_manager.py` / `downloader.py`)
為此專案新增的另一項重要核心。
- **背景任務池**：使用 `asyncio.get_event_loop().run_in_executor()` 來執行 `yt-dlp` 這個容易產生阻擋行為的高延遲任務。
- **分離式儲存策略**：
  - **`/app/data/downloads`**：給定長久保留的使用者下載音訊/影片。
  - **`/app/data/cache`**：作為短期或自動快取區，並且有 `_enforce_cache_limit()` 定期清除舊的資源 (LRU 機制)。

### 2.3. Invidious 代理 (The Bone)
- **職責**：因為直接 Parse YouTube 經常失敗，必須依賴 `ytlite-engine`。它不僅擋下 YouTube Rate-limit 的問題，還提供了簡化版的 REST API 供我們的 FastAPI 獲取 Metadata。
- **儲存**：依賴 `ytlite-postgres` 作為它的 Channel 狀態快取庫。

### 2.4. 客戶端 (The Skin)
- **技術棧**：原生 HTML5 + Vanilla JS (`templates/`)，無 NPM 框架。
- **相容性考量**：
  - 因為 iOS 12 不支援某些跨域資源或是較新版本的 fetch / Array API，全部採用保守語意攥寫。
  - 核心痛點「播放不穩定」的解法：主播放器雖然可以抓 Invidious 直連 MP4 檔，但以 `YouTube Iframe API` 為保底（Fallback），以確保持續可看性。
  - **PWA (Progressive Web App)**：支援加到主畫面，支援迷你背景播放體驗。

---

## 3. 資料與權限流轉（Data Flow）

1. **認證流 (Auth Flow)**：
   - 點擊登入 -> FastAPI 重導向至 `accounts.google.com` (請求唯讀 YT 權限)。
   - Callback -> `oauth2callback` -> Google 給予 Token。
   - API 將 Token 寫入 `/app/data/sessions/{session_id}.json` 並設定給 Client。

2. **頁面/影片載入流 (Feed Flow)**：
   - 使用者發出主頁請求 `/`。
   - `main.py` 平行發送要求給 Invidious (獲取 trending/search) 與 Google API (獲取訂閱清單)。
   - 將兩者進行 Merge、去除 Blocklist。
   - 輸出給 `base.html` 中渲染成 Cards。

3. **背景下載流 (Download/Cache Flow)**：
   - 使用者點選「下載 MP3」或背景自動快取 -> 發出 `/api/download` POST 請求
     （`main.py:1167`。**不是** `/api/downloads/add`，本文件曾誤記為後者，2026-08-09 實測更正：
     整個 `webbox/src/middleware/` 內 `/api/downloads/add` 字面命中 0，控制組 `/api/download` 命中 29）。
   - `queue_manager.add_job` 生成唯一 Job ID（uuid4），丟入內部 Queue。
   - `_worker` 背景協程透過 `downloader.py` (呼叫 yt-dlp) 開始抓取。進度寫入 Job dict。
   - **mp3 後處理鏈（順序是承載性的）**：`FFmpegExtractAudio` → `FFmpegMetadata`（寫 ID3
     title/artist/album）→ `EmbedThumbnail`（嵌封面）。搭配 opts 層的 `writethumbnail`。
     yt-dlp 的 artist 回退鏈（`ffmpeg.py:751`）含 `uploader`，所以一般影片（無 artist 欄位）
     拿到頻道名，`- Topic` 自動頻道則拿到真實演出者——故**不得加 `parse_metadata` 映射**，
     那會覆蓋掉後者。mp3 的嵌圖走 ffmpeg（`embedthumbnail.py:90-96`），不需 mutagen；
     ogg/opus/flac 分支才硬需求它（`:198`）。
   - 網頁透過 `/api/downloads` 輪詢取得即時 % 數，並在 UI (`dl-status-pill`) 上繪製進度。
   - 清單移除與刪檔是**解耦的**：`DELETE /api/downloads/{job_id}?purge=bool`，`purge` 預設 `False`。
     磁碟上的歷史檔經 `rescan_download_dir()` 重建時一律標 `archived`（**絕不是** `completed`，
     後者會被前端自動存檔路徑當成「剛下載完可以從伺服器刪除」）。

---

## 4. 基礎架構與部署方式
本專案採用 `docker-compose.yml` 進行服務一體化部署，並利用 `webctl.sh` 控制啟停。

- **網路隔離**：外部只開 Port `1214` 介接 FastAPI，並可掛載 Nginx。
- **資料庫與內部服務**：`ytlite-engine` (1215) 與 `ytlite-postgres` (1216) 皆跑在 Docker 內部網路 `3000`/`5432`，受中介層完全保護。
- **檔案權限**：/app/data 映射至本地磁碟區 `/opt/ytlite_v3/user_db` (包含下載、快取與使用者檔案)，確保 Container 重建後資料必定保留。
