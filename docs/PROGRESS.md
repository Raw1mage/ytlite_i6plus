# YT Lite v3 進度摘要（繁體）

## 本階段目標
- 以 FastAPI + Invidious 服務舊款 iPhone 6 Plus，提供繁中介面與穩定播放。
- 透過 iframe 播放避免直抓串流失敗，維持輕量前端。

## 已完成
- 基礎環境：Docker Compose（三服務）、埠位 1214/1215/1216，`webctl.sh` 管理腳本
- FastAPI 中介層、Jinja2 模板、ProxyHeadersMiddleware（支援 Nginx/HTTPS）
- Google OAuth2 登入/登出、Session 保存
- `/api/videos` 繁中搜尋代理（台灣熱門/新聞/直播/Podcast）與縮圖 URL 修正
- UI：行動優先網格、分類 Chips、Drawer、搜尋框
- 播放器：全螢幕/迷你、iframe 播放回退、無快取標頭
- **功能修復 (2025-12-15)**:
    - 相關影片 ("Next Up") 功能實作 (來自 Invidious `recommendedVideos`)。
    - Header Z-Index 與點擊問題修復。
    - 播放介面 UI 間距 (Aspect Ratio) 與 Back Button 邏輯優化。
    - 搜尋結果頁面分類按鈕修復。

## 現況
- 影片清單與縮圖正常，分類可切換。
- 搜尋功能正常，播放器 UI 與互動修復完畢。
- iframe 播放穩定；相關影片已可顯示並點擊播放。
- OAuth token 儲存於 `/app/data/token.json`（Docker 掛載）。

## 待處理
1) 訂閱/資料
- [x] `/api/subscriptions` 取回訂閱並呈現於 Drawer
- [x] 訂閱 Feed 聚合（首頁混合顯示）
- [x] 自訂導覽與封鎖管理
- [ ] LocalStorage 觀看歷史 + Drawer 分頁

2) 搜尋
- [x] 搜尋結果為空／未登入狀態 (主要流程已修復，需持續觀察)
- [ ] 搜尋結果頁模板完善並支援播放 (目前已可播放，需優化介面)
- [ ] 最近搜尋記錄

3) 體驗/品質
- [ ] Metadata 回退策略
- [ ] 無限捲動
- [ ] PWA/快取（Manifest、Service Worker）
- [ ] 播放進度記錄/恢復

## 風險
- Invidious 偶有 403/500：播放已改用 iframe；可考慮備援實例或快取。
- YouTube API 配額：訂閱同步需控頻率或改手動觸發。
- 舊機效能：持續限制 JS 量與 DOM 複雜度。
