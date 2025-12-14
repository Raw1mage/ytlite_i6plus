# 除錯紀錄（精簡版，繁體）

本檔彙總近期除錯重點；完整長文請見 `docs/HISTORY/DEBUG_LOG.md`。

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
