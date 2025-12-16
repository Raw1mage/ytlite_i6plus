# 除錯紀錄（精簡版，繁體）

本檔彙總近期除錯重點；完整長文請見 `docs/HISTORY/DEBUG_LOG.md`。

## 2025-12-16：Drawer 訂閱列表顯示空白（✅）
- **症狀**：側邊抽屜「訂閱內容」顯示 `No subscriptions found.`，即使已登入且後端回傳訂閱清單。
- **原因**：前端僅處理純陣列回傳，未解析 `/api/subscriptions` 的 `{ subscriptions: [...] }` 物件。
- **處置**：前端改為優先取 `data.subscriptions`；若本身為陣列則沿用。

## 2025-12-14：v3 重構—影片清單與播放（✅）
- **Session ID**：2025-12-14_v3_refactor（21:45 UTC+8）
- **狀態**：成功

## 2025-12-15：搜尋與登入狀態異常（🟠 未解）
- **症狀**：搜尋頁顯示未登入、結果為 0；前端 console 出現 `openPlayer not available`；頻道連結有時 404，播放畫面頻道資訊卡在 Loading。
- **環境限制**：沙箱無法存取本機 Docker log，後台日誌需由本機提供。
- **目前推測/檢查點**：
  - 確認 Invidious `/api/v1/search` 回應（status/JSON 是否錯誤）；`logged_in` 是否有正確傳到模板。
  - 確認 `/channel` 路由是否被 Trailing slash/反向代理改寫；前端帶的 `channel_id` 是否為空。
  - 播放 overlay 關閉時已清空 iframe/停止音訊，待再次驗證。
- **TODO**：取得後台 log 以釐清搜尋/登入狀態；修正模板與會話傳遞；實作播放進度記錄。

### 問題摘要
| ID | 嚴重度 | 標題 | 狀態 | 時間 |
|----|--------|------|------|------|
| UI-001 | 高 | Header 遮蔽內容 | ✅ 21:15 |
| UI-002 | 中 | Header 佈局錯位 | ✅ 21:20 |
| UI-003 | 高 | Header 跑到頁底 | ✅ 21:38 |
| INFRA-001 | 重大 | Invidious `/trending` 500 | ✅ 21:30 |
| INFRA-002 | 中 | 3000 埠衝突 | ✅ 21:27 |
| INFRA-003 | 高 | 縮圖無法顯示 | ✅ 21:42 |
| INFRA-004 | 中 | 內容語系錯誤 | ✅ 21:40 |
| CODE-001 | 高 | 函式命名不一致 | ✅ 21:35 |
| AUTH-001 | 中 | OAuth Scope 警告 | ✅ 20:58 |
| DEP-001 | 高 | 缺少 itsdangerous | ✅ 20:52 |
| DEP-002 | 低 | 缺少 Response import | ✅ 21:05 |
| PLAY-001 | 高 | 影片播放失敗 | ✅ 22:15 |
| UI-004 | 高 | Player 初始化錯誤 | ✅ 22:00 |
| UI-005 | 中 | Player 尺寸/樣式錯誤 | ✅ 22:20 |

### 重點修正
- Header 改用 `position: sticky`，移除 body padding，並將 chips 移入 Header。
- DOM 順序調整，Header 置頂，避免被 Drawer/Overlay 蓋住。
- Invidious `trending` 改為繁中搜尋 `/search`（台灣熱門/新聞/直播/Podcast）。
- Docker 內部縮圖網址改寫成外部可存取的 `http://localhost:1215`，並提供 YouTube CDN 後備。
- 修正函式命名（`loadCategory`）與缺漏的 DOM 元件 `mini-title`。
- 播放策略改為 YouTube iframe，移除不穩定的直抓串流邏輯。
- OAuth 設定 `OAUTHLIB_RELAX_TOKEN_SCOPE=1`，補齊 `itsdangerous` 與 `Response` 依賴。
- Player 樣式強制全螢幕/60vh，避免黑屏與極小畫面。

## 2025-12-13：依賴安裝（iOS）
- `flask`、`yt-dlp` 安裝時因缺乏編譯器觸發 `MarkupSafe` 編譯錯誤；pip 自動回退到可用的 wheel，無需額外處置。未來需要 C 擴充套件（例如 `numpy`）時，需尋找 iOS/Procursus 的預編譯套件。
- iOS 上無 `pip`：透過 `python3 -m ensurepip` 重新安裝。
# Debug Log & Root Cause Analysis

## 2025-12-15: Video Player UI Layout Regression

### Issue Description
Attempted to remove the vertical black gap (letterboxing) below the video player in the overlay. The user reported that the modification caused:
1.  Video player becoming full screen with excessive gaps.
2.  Info/Description section disappearing.
3.  Navigation bar buttons becoming unclickable.
4.  "Back" navigation issues where the URL changed but the UI remained stuck.

### Root Cause Analysis (RCA)
1.  **CSS Layout Conflict**: The original layout relied on a fixed `min-height: 60vh` for the `.video-section`. The attempt to switch to a pure aspect-ratio hack (`padding-bottom: 56.25%` with `height: 0`) within a Flexbox container (`.overlay-container`) likely caused the container to miscalculate availability height, pushing the `.full-info` block out of the viewport or collapsing it.
2.  **Z-Index War**: In an attempt to ensure the overlay covered the content, `z-index` values were modified. The overlay's `z-index` (1050) was accidentally set higher than or effectively blocking the header's interactivity context, or the full-screen video expansion overlapped the fixed header.
3.  **Aggressive Refactoring**: Too many CSS properties (margins, paddings, display offsets) were changed simultaneously without visual verification, leading to a "broken state" rather than a marginal improvement.

### Resolution
Reverted `base.html` to the known stable state (approx Step 2502). This restored the `60vh` fixed height, ensuring the info section is visible and the header remains interactive. The navigation logic for `popstate` was kept as it was robust, but the CSS was rolled back.

### Lessons Learned
- CSS Layout changes involving Flexbox and Aspect Ratio hacks on mobile identifiers (like iPhone 6 Plus simulation) are fragile.
- Avoid modifying global `z-index` hierarchies without a complete map of layers.
- Incremental CSS changes are safer than rewriting entire block styles.

---

## Incident Log: 2025-12-15 - Black Screen & DB Crash

### What Changed
- **Frontend (`base.html`)**: Adjusted `footer` z-index, modified `openPlayer` to use `related_videos` from API, changed CSS for `.video-wrapper` (aspect-ratio hack).
- **Backend (`main.py`)**: Updated `/api/get_stream` to include `recommendedVideos` in response.
- **Environment**: Executed `./webctl.sh restart`.

### Symptoms
- User reported "No video screen" (black screen below header).
- Navigation bar visible (header).
- Content (Grid) missing.
- Screenshot confirms black body content.

### Root Cause Analysis
1.  **DB Failure (Primary)**: The `docker restart` command failed for `ytlite-postgres` with an OCI runtime error (mount issue). The container exited (Status: Exited 127).
    - Without the database, Invidious cannot perform searches.
    - `main.py` catches the error and returns empty video lists.
    - `index.html` receives empty list, clears the grid, and shows nothing (no "Loading", just empty).
2.  **Code Issues (Secondary)**: 
    - A ReferenceError (`count is not defined`) was introduced in `./base.html` because a variable check was left outside its defining block scope during the multi-replace edit. This likely would have caused `openPlayer` to crash, but the primary black screen is due to the DB.

### Action Plan
1.  **Revert**: Rollback `main.py` and `base.html` to previous state. (DONE)
2.  **Recover**: Hard restart Docker containers (`docker-compose down && up`) to fix the mount/DB issue.
3.  **Retry Check**: Verify app is working (displaying videos) before attempting fixes again.
