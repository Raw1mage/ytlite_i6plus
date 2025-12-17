# YT Lite v3 開發計畫與進度 (Roadmap & Status)
> 目標：為 iPhone 6 Plus (iOS 12) 提供輕量、無廣告、繁中優先的 YouTube 體驗，運算集中於 PC/WSL 中介層。

## 系統架構
- **前端 Web**：Safari WebClip / PWA (HTML5 + Vanilla JS)，行動優先設計。
- **中介層 API**：FastAPI (Port 1214)，負責：
  - Google OAuth2 授權與 Session 管理
  - Invidious API 代理與資料聚合 (Feed 混合)
  - 縮圖 URL 修正與模板渲染 (Jinja2)
- **資料與抓取**：
  - Invidious 實例 (Port 1215) + PostgreSQL (Port 1216)
  - YouTube Data API (用於訂閱同步)
- **部署**：Docker Compose 管理服務，可選 Nginx 反向代理。

## 目前狀態 (Current Status)
- **核心功能已就緒**：登入、訂閱同步、首頁混合 Feed、搜尋、播放 (iframe) 均正常運作。
- **高度客製化**：使用者可自訂導覽 Chips 與封鎖特定頻道。
- **穩定性**：已解決大部分 Invidious 403 問題 (改用 iframe)，播放器 UI 已修復。
- **待優化**：觀看歷史、無限捲動、以及 Metadata 載入失敗時的備援顯示。

---

## 發展路線圖 (Roadmap)

### ✅ 已完成 (Phase 1: 基礎架構與播放)
- [x] **環境建置**：Docker Compose (Postgres, Invidious, Middleware) 與埠位配置。
- [x] **中介層開發**：FastAPI + Jinja2 模板框架，ProxyHeaders 支援。
- [x] **繁中內容優化**：預設搜尋台灣熱門、新聞、直播、Podcast。
- [x] **行動 UI**：響應式網格、分類 Chips、側邊欄 (Drawer)、全螢幕與迷你播放器。
- [x] **播放策略**：改用 YouTube iframe 以解決 Invidious 串流不穩問題。
- [x] **功能修復 (12/15)**：相關影片 (Next Up)、Header Z-Index、UI 間距與按鈕邏輯。

### ✅ 已完成 (Phase 2: 個人化與管理)
- [x] **Google OAuth2**：登入/登出流程，Session 安全儲存。
- [x] **訂閱同步**：整合 YouTube Data API，自動同步訂閱清單至 Drawer。
- [x] **首頁 Feed**：已登入使用者首頁自動混合「訂閱頻道最新影片」與「熱門推薦」。
- [x] **自訂導覽**：後端 `/api/nav` 儲存設定，提供 `/manage/nav` 前端管理介面。
- [x] **封鎖管理**：可封鎖特定頻道 (ID/Name)，自動過濾搜尋與首頁內容。
- [x] **搜尋功能**：`/search` 路由與結果頁模板實作，支援語音輸入。

### 🚧 進行中 (Phase 3: 體驗優化)
- [ ] **觀看歷史**：
  - 前端 LocalStorage 紀錄觀看影片。
  - Drawer 新增「觀看歷史」分頁讀取紀錄。
- [ ] **Metadata 回退機制**：
  - 當 Invidious API 失敗 (Loading...) 時，前端/後端的優雅降級策略。
- [ ] **無限捲動 (Infinite Scroll)**：
  - 首頁與搜尋結果的自動加載下一頁。

### 📅 待排期 (Backlog)
- [ ] **PWA 進階**：Manifest 設定、Service Worker 快取 (離線瀏覽)。
- [ ] **播放優化**：
  - 影片畫質選擇 (目前 iframe 自動，未來可研議 Invidious 直接串流切換)。
  - 播放清單管理。
  - 播放進度記憶與恢復。
- [ ] **社群功能**：讀取影片留言區。
- [ ] **推播通知**：訂閱頻道新片通知 (需評估 iOS 支援度)。

---

## 風險與對策
- **Invidious 穩定性**：
  - *風險*：API 變更或 403 錯誤導致無法抓取。
  - *對策*：維持 iframe 播放為主要策略；考慮實作 Server-side Cache 或多實例備援。
- **YouTube API 配額**：
  - *風險*：訂閱同步消耗過多 Quota。
  - *對策*：目前採手動/登入時同步，未來可增加快取時間或限制同步頻率。
- **舊機效能 (iPhone 6+)**：
  - *風險*：複雜 DOM 或 JS 導致卡頓。
  - *對策*：堅持使用 Vanilla JS，避免大型框架 (React/Vue)，減少動畫特效。

## 更新紀錄 (Changelog)
- **2025-12-14**：架構調整，核心播放策略改為 iframe，修正全螢幕播放器與縮圖。
- **2025-12-15**：修復相關影片顯示、UI 層級與互動問題。
- **2025-12-16**：釋出 v3.1，新增導覽 Chips 自訂、訂閱同步、混合 Feed 與封鎖管理功能。
