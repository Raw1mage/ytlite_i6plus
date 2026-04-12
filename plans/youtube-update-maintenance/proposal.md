# Proposal

## Why

- YouTube 播放與抓取機制會持續變動，`yt-dlp` 與 Invidious 需要定期更新。
- 現在的 log 與文件不足以快速定位是套件過舊、站點改版，還是容器/前端相容性問題。
- 需要一份固定 SOP，讓每次失效都能照流程處理，而不是臨時排查。

## Original Requirement Wording (Baseline)

- 「請查網站運作log。youtube截取機制又失效了。是不是要更新套件了」
- 「建立/plans資料夾，並在裏面用planner skill建立一個定期更新計畫。把整個程式需要調整更新的地方都列出來變成sop」
- 「請參照~/projects/skills找相關skill」

## Requirement Revision History

- 2026-04-12：先建立單檔 SOP，之後依 planner skill 改成 active plan package。
- 2026-04-12：補上 plan 目錄結構與標準化文件分工。
- 2026-04-12：盤點完成，確認 RCA 為依賴過舊。計畫從「僅建 SOP」升級為「建 SOP + 實施最小修復」。

## Effective Requirement Description

1. 建立一個符合 planner skill 的 `plans/` plan package。
2. 內容需涵蓋 YouTube 截取機制、下載器、Invidious、容器依賴、前端播放、日誌與驗收。
3. 產出可作為後續定期維護的 SOP。
4. **立即實施最小修復**：升級 yt-dlp 與 Invidious 至當前穩定版，重建容器使服務恢復。

## RCA（根因分析）

### 問題現象

Web 服務無法播放或下載 YouTube 影片。先前可正常使用。

### 根因

1. **Invidious image 用 `latest` 且未重建** — YouTube 改版後 Invidious 需要更新才能解析新頁面結構，但容器映像停留在舊版。
2. **yt-dlp 無版本固定** — `requirements.txt` 只寫 `yt-dlp`，Docker image 上次 build 時安裝的版本已過時，無法處理 YouTube 新格式。
3. **無診斷能力** — `quiet: True` 壓制 yt-dlp 日誌、Invidious 失敗只回空結果，無法快速定位是哪一層壞。

### 修復策略

最小修復路徑：不動 runtime 邏輯，只升級依賴到當前穩定版並重建容器。

## Scope

### IN

- 定義定期更新流程（SOP）。
- 列出需檢查的關鍵檔案。
- 明列故障排查順序與驗收條件。
- **固定 yt-dlp 版本為 `2026.3.17`**。
- **固定 Invidious image tag 為最新穩定版**。
- **重建 Docker containers**。

### OUT

- 不重寫下載器邏輯或播放機制。
- 不新增框架或監控系統。
- 不處理與 YouTube 無關的功能開發。

## Non-Goals

- 不是重新設計整個下載架構。
- 不是替代實際監控系統的正式告警方案。

## Constraints

- 必須符合 `planner` skill 的 plan package 結構。
- 必須保留對舊裝置與現有 Docker 架構的相容性。
- 必須先建立可操作 SOP，再談程式變更。

## What Changes

- 新增一個 active maintenance plan package。
- 將更新項目整理成可重複執行的文件。
- 把風險、檢查點與驗收方式明確化。

## Capabilities

### New Capabilities

- 定期更新 SOP：可按週或故障事件執行。
- 影響面清單：明確知道哪些檔案需要一起看。
- 排查路徑：可區分套件問題、站點變動與部署問題。

### Modified Capabilities

- 現有維護方式：由臨時查 log 改為文件化排查。
- 現有變更流程：由口頭經驗改為 plan 驅動。

## Impact

- 影響 `webbox/src/middleware/` 的下載與播放模組。
- 影響 `webbox/BUILD/` 與 `webbox/docker-compose.yml` 的部署維護。
- 影響 `docs/ARCHITECTURE.md` 與 `docs/events/` 的知識沉澱。

