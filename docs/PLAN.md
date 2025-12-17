# YT Lite v3 開發計畫與路線圖
> 目標：為 iPhone 6 Plus 提供輕量、無廣告、繁中優先的 YouTube 體驗，運算集中於 PC/WSL 中介層。

## 架構概覽
- **前端**：Safari WebClip/PWA（繁體 UI、iframe 播放）。
- **中介層**：FastAPI（1214），負責 OAuth、Invidious 代理、模板與縮圖修正。
- **抓取/資料**：Invidious（1215）＋ PostgreSQL（1216）。
- **代理**：Nginx/HTTPS（選用），統一域名與回呼。

## 已完成
- [x] Docker Compose 服務（Postgres、Invidious、中介層）與埠位調整（1214/1215/1216）
- [x] FastAPI 中介層 + Jinja2 模板
- [x] Google OAuth2 登入/登出流程
- [x] 繁體中文內容搜尋（台灣熱門/新聞/直播/Podcast）
- [x] 縮圖 URL 修正（Docker 內部位址改外部可存取）
- [x] 行動優先 UI、分類 Chips、Drawer、搜尋框
- [x] 全螢幕播放器（可最小化），播放策略改用 YouTube iframe
- [x] 訂閱同步：從 YouTube API 取訂閱清單，顯示於 Drawer
- [x] 訂閱 Feed：已登入者首頁「全部」分頁自動混合訂閱頻道最新影片
- [x] 自訂導覽 Chips：後端儲存設定，提供導覽管理介面 (/manage/nav)
- [x] 封鎖管理：可封鎖特定頻道不顯示於搜尋或首頁
- [x] 搜尋功能：已實作 /search 路由與結果頁模板

## 進行中
- [ ] 觀看歷史：前端 LocalStorage 紀錄 + Drawer 分頁

## 即將進行
- [ ] Metadata 回退：Invidious 失敗時的替代資訊來源/顯示策略
- [ ] UI/體驗：無限捲動、錯誤提示優化

## 待規劃/未排期
- [ ] PWA：Manifest、Service Worker（快取與離線）
- [ ] 影片畫質選擇
- [ ] 播放清單管理、留言區
- [ ] 推播/通知

## 風險與對策
- **Invidious 不穩**：以 iframe 為主要播放，metadata 失敗不阻斷；可考慮備援實例或 API 快取。
- **YouTube API 配額**：訂閱同步受限，必要時降低頻率或改為手動觸發。
- **舊機效能**：避免複雜前端框架與過度 JS，保持簡化 UI。

## 更新紀錄
- **2025-12-14**：播放策略改為 iframe，修正全螢幕播放器樣式與縮圖 URL。
- **2025-12-16**：新增導覽 Chips 自訂功能、訂閱同步與首頁 Feed 混合、封鎖頻道管理。
