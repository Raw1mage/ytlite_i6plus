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
  - **`/app/data/cache`**：作為短期或自動快取區，並且有 `_enforce_cache_limit()` 定期清除舊的資源。
    **注意：它現在是「建立時間排序」而非真正的 LRU**（2026-08-10）。唯一寫入 mtime 的
    `os.utime` touch 附著在磁碟去重分支上，該分支已依使用者裁示移除（見下方「檔名即真實來源」），
    所以重新請求的快取項不再移到驅逐佇列尾端。100MB 上限的驅逐本身仍運作。
    保留 touch 就得保留「找到那個檔以便 touch」的查詢，而那個查詢正是被移除的東西。

- **檔名策略：標題即檔名，且沒有伺服器端的下載歷史**（`7f9fda2`，2026-08-10）
  - `outtmpl = '%(title,id).59s.%(ext)s'` + `windowsfilenames=True`。**落地那一刻就是純標題**，
    不再是 `{video_id}.%(ext)s`。逗號 fallback 是承載性的：裸 `%(title)s` 在 title 缺失時
    產出 `NA.mp3`，多支影片互相覆蓋。
  - **最終路徑取自 yt-dlp 自報的 `info['requested_downloads'][0]['filepath']`**。
    ⚠ **不是** top-level 的 `info['filepath']` —— 後者恆為 `None`。兩者同名但不同物件
    （前者是 `extract_info` 回傳的 dict，後者是 postprocessor 收到的 dict）。實測坐實。
    取不到時以嵌入 id 反查（`_locate_output`），**絕不編造路徑**；真的找不到就標 `error`，
    因為一個 `completed` 但指向不存在檔案的 job 會讓存檔/刪除/大小全部壞掉而 UI 看起來正常。
  - **byte 預算**：ext4 `NAME_MAX` 實測 255 bytes（256 即 `OSError errno=36`），而 `.59s`
    數的是**字元不是 bytes**。所以衝突後綴與最長暫存後綴（`.f251.webm.part` = 15B）
    必須**從 title 預算裡扣掉**，不可串接；截斷用 `_fit_bytes()` 逐字元累加，
    不用 `errors='ignore'`（那會把「切壞了」偽裝成「切好了」）。
  - **同標題衝突加 ` (2)` 後綴**。兩支不同影片可以有相同標題，舊的 `{video_id}` 命名
    在結構上不可能發生這件事：同名 ⇒ 同路徑 ⇒ 後者靜默覆蓋前者，而 tag 仍是前者的 id。
  - **伺服器不記得下載過什麼**（使用者裁示）。已移除：磁碟 `os.path.exists(f"{video_id}.{ext}")`
    去重、`LEGACY_NAME` 分支、cache↔downloads 交叉複製。`add_job` 的 in-memory 迴圈
    **必須把 `ARCHIVED_STATUS` 一併排除** —— `rescan` 會為磁碟上每個檔重建 job，
    否則幾週前下載的檔會在此命中而回傳 archived job：**同一個「持久記憶」語意從記憶體
    繞回來**。刪掉一條路徑不等於刪掉那個行為。
  - **`video_id` 仍必須可還原，但那不是歷史記憶**：兩個模板各有一處把它插進
    `https://i.ytimg.com/vi/${job.video_id}/default.jpg`。檔名改成標題後 stem 含空格與 `#`
    會讓縮圖 URL 全壞，故 `rescan` 改為從檔案讀回真 id（xattr `user.ytlite.video_id` 為主、
    ID3 `purl`/`TXXX` 為副、stem 為最後退路）。判準是「這個讀取是為了記得過去，
    還是處理眼前這一次」——縮圖與「找剛下載完的那個檔」都屬後者。

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
