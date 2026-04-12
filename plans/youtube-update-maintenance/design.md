# Design

## Context

- 專案使用 FastAPI middleware 透過 `yt-dlp` 下載、Invidious 提供 metadata，前端則以傳統模板與 iframe 播放。
- `logs/watcher.log` 目前只顯示 signal 轉發，診斷資訊不足。
- `yt-dlp` 與 YouTube 的相依關係高度動態，必須把更新流程文件化。

## Goals / Non-Goals

**Goals:**

- 建立可執行的定期更新 SOP。
- 列出會受 YouTube 改版影響的關鍵檔案。
- 讓後續維護有固定驗收與回歸檢查。

**Non-Goals:**

- 不改動現有下載流程邏輯。
- 不導入新的框架或監控系統。

## Decisions

- 以 `plans/youtube-update-maintenance/` 作為 active plan package，因為它對應 planner skill 的標準結構。
- 以 SOP 形式列出所有影響面，而不是只寫單點修補，因為這類失效會重複出現。
- 把 log、容器、前端與 Invidious 一起納入清單，避免只更新 `yt-dlp` 卻漏掉其他相依面。

## Data / State / Control Flow

- 使用者回報失效 -> 先看 `logs/watcher.log` 與服務 log -> 判斷是下載器、Invidious、前端播放器或部署問題 -> 決定是否更新依賴 -> 驗收影片與 playlist 播放是否恢復。

## RCA Summary

| 根因 | 影響範圍 | 修復動作 |
|------|---------|---------|
| yt-dlp 未固定版本，Docker image 內版本過舊 | 下載路徑全部失敗 | 固定 `yt-dlp==2026.3.17` |
| Invidious 用 `latest` 未重建，無法解析 YouTube 新頁面 | 串流播放全部失敗 | 固定 Invidious image tag |
| `quiet: True` 壓制 yt-dlp 日誌 | 無法快速診斷 | 後續改善項（本次不動 runtime） |

## Risks / Trade-offs

- `yt-dlp` 更新後仍可能失效 -> 必須準備補上額外 runtime 或 cookie 參數。
- 只寫文件不改 log 可能仍難診斷 -> SOP 需明列後續程式需補強的 log 點。
- 固定版本後需手動追蹤新版 -> SOP 需包含定期檢查版本的步驟。

## Critical Files

- `webbox/src/middleware/downloader.py`
- `webbox/src/middleware/queue_manager.py`
- `webbox/src/middleware/main.py`
- `webbox/requirements.txt`
- `webbox/BUILD/middleware/Dockerfile`
- `webbox/docker-compose.yml`
- `webbox/BUILD/invidious/config.yml`
- `logs/watcher.log`
- `docs/ARCHITECTURE.md`

