# 除錯記錄（完整版，繁體）

**Session ID**：2025-12-14_v3_refactor  
**時間**：2025-12-14 21:45 UTC+8  
**階段**：影片清單與播放重構  
**狀態**：✅ 成功

---

## 問題摘要

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
| UI-006 | 中 | Metadata 載入失敗 | ⚠️ 部分 |

---

## 詳細記錄

### UI-001 Header 遮蔽內容
- **原因**：Header 用 `position: fixed`，body padding 設得不足。
- **處置**：改用 `position: sticky`，移除 body padding，Header padding 縮小，並調整 chips 容器間距。
- **結果**：內容不再被遮蔽。

### UI-002 Header 佈局錯位
- **原因**：分類 Chips 放在內容區，未與搜尋/登入對齊。
- **處置**：將 Chips 移入 Header，Flex 排列為 `[Logo][Chips] — [Search][Login]`。

### UI-003 Header 跑到頁底
- **原因**：DOM 排序錯誤，Header 放在 Drawer/Overlay 之後。
- **處置**：重排 body 結構，Header 置頂，其餘在後。

### INFRA-001 Invidious `/trending` 500
- **原因**：YouTube 封鎖 trending 抓取。
- **處置**：改用繁中關鍵字搜尋 `/api/v1/search?q=台灣熱門...`；分類對應：全部/新聞/直播/Podcast。

### INFRA-002 3000 埠衝突
- **原因**：既有 Node 服務占用 3000。
- **處置**：Port 重新分配 1214（中介層）/1215（Invidious）/1216（Postgres），Compose 更新。

### INFRA-003 縮圖無法顯示
- **原因**：Invidious 回傳 `http://invidious:3000` 內部位址或相對路徑。
- **處置**：程式改寫縮圖為 `http://localhost:1215/...`，相對路徑前置主機；無縮圖則退回 YouTube CDN。

### INFRA-004 內容語系錯誤
- **原因**：搜尋使用英文關鍵字。
- **處置**：改用繁中關鍵字（台灣熱門/新聞/直播/中文 podcast）。

### CODE-001 函式命名不一致
- **原因**：模板呼叫 `loadCategory`，實作名稱不符。
- **處置**：統一命名。

### AUTH-001 OAuth Scope 警告
- **原因**：Scope 嚴格檢查。
- **處置**：設定 `OAUTHLIB_RELAX_TOKEN_SCOPE=1`。

### DEP-001/002 缺少依賴
- **原因**：套件列缺 `itsdangerous`，程式缺 `Response` import。
- **處置**：補齊 requirements 與 import。

### PLAY-001 影片播放失敗
- **原因**：缺少 DOM 元件 `mini-title`；`get_stream` 無可用串流時報錯。
- **處置**：新增缺漏元素，移除直抓串流邏輯，改以 YouTube iframe 可靠播放並加上 cache-busting。

### UI-004 Player 初始化錯誤
- **原因**：JS 存取不存在的 `mini-title`。
- **處置**：補元素並加 null 檢查。

### UI-005 Player 尺寸/樣式錯誤
- **原因**：CSS 優先度與高度設定不足，迷你樣式殘留。
- **處置**：JS 強制全螢幕樣式，`.video-section/.video-wrapper` 設 `min-height: 60vh`。

### UI-006 Metadata 載入失敗（部分）
- **原因**：`get_stream` 失敗時拒絕資料，導致頻道/描述為「Loading...」。
- **處置**：播放已用 iframe 不受影響，metadata 保持嘗試但不阻斷；仍需後續回退策略。

---

## 服務狀態（當日）

| 服務 | 狀態 | 埠 |
|------|------|----|
| PostgreSQL | 🟢 | 1216 |
| Invidious | 🟢 | 1215 |
| Middleware | 🟢 | 1214 |
| Endpoint | Status | Description |
|----------|--------|-------------|
| `http://localhost:1214` | 🟢 Accessible | Video feed & Playback working |
| `https://ytlite.sob.com.tw` | 🟢 Accessible | Via Nginx reverse proxy |
| `http://localhost:1215` | 🟢 Accessible | Invidious API |
| `http://localhost:1216` | 🟢 Accessible | PostgreSQL |

### Features
| Feature | Status |
|---------|--------|
| Video Feed | ✅ Working |
| Video Playback | ✅ Working (Iframe) |
| Thumbnails | ✅ Working |
| Categories | ✅ Working |
| Search UI | ✅ Ready |
| OAuth Login | ✅ Working |

---

## Achievements 🎉

1. ✅ **First page fully functional** with video grid
2. ✅ **Video Playback Functional** via YouTube Embed
3. ✅ **Traditional Chinese content** localization
4. ✅ **All thumbnails displaying** correctly
5. ✅ **Clean UI** with proper layout & Fullscreen Player
6. ✅ **All critical bugs resolved**

---

## Next Steps

1. **Add subscription feed** - Display user's subscribed channels
2. **Implement search functionality** - Make search box functional
3. **Add watch history** - Store in localStorage
4. **Optimize performance** - Lazy loading, infinite scroll

---

*Last Updated: 2025-12-14 22:30:00 +08:00*
