# Implementation Spec

## Goal

- 建立一個可長期維護的 YouTube / yt-dlp 更新 SOP 與對應 plan package，讓後續失效時能快速定位要更新的程式與部署點。

## Scope

### IN

- **升級 yt-dlp 至 `2026.3.17`**（固定於 `webbox/requirements.txt`）。
- **固定 Invidious image tag**（於 `webbox/docker-compose.yml`）。
- 重建 Docker containers 使修復生效。
- 整理所有與 YouTube 截取、播放、下載、快取、部署依賴相關的更新清單。
- 將更新流程拆成可執行的維護步驟與驗收條件。
- 明列需要持續檢查的程式檔案、容器設定與日誌位置。

### OUT

- 不修改 runtime 程式邏輯（downloader.py, main.py 不動）。
- 不新增框架或監控系統。
- 不處理與 YouTube 無關的功能開發。

## Assumptions

- 專案會持續使用 `yt-dlp`、Invidious 與 FastAPI middleware 這條架構。
- `plans/` 會作為 active plan storage，供後續追蹤與更新。
- 後續實作時會依此 plan 再開一輪變更。

## Stop Gates

- 如果發現需要同步改動 runtime 程式，必須先回到 plan 再拆分任務。
- 如果 `yt-dlp` 或 YouTube 的變動需要新增外部依賴，必須先確認部署環境是否支援。
- 如果現有 log 無法支持診斷，必須先補 log 再進行功能更新。

## Critical Files

- `webbox/src/middleware/downloader.py`
- `webbox/src/middleware/queue_manager.py`
- `webbox/src/middleware/main.py`
- `webbox/requirements.txt`
- `webbox/BUILD/middleware/Dockerfile`
- `webbox/docker-compose.yml`
- `webbox/BUILD/invidious/config.yml`
- `webbox/src/middleware/templates/base.html`
- `webbox/src/middleware/templates/watch.html`
- `webbox/src/middleware/templates/playlist.html`
- `webbox/src/middleware/templates/channel.html`
- `logs/watcher.log`
- `logs/chrome_preview.log`
- `docs/ARCHITECTURE.md`
- `docs/events/`

## Structured Execution Phases

### Phase 1: 最小修復（恢復服務）

1. 修改 `webbox/requirements.txt`：`yt-dlp` → `yt-dlp==2026.3.17`
2. 修改 `webbox/docker-compose.yml`：Invidious image 從 `latest` 改為固定穩定版本 tag
3. 執行 `docker compose build --no-cache && docker compose up -d`
4. 驗證播放與下載功能

### Phase 2: SOP 文件化

5. 列出所有會受 YouTube 變動影響的程式與部署檔，建立更新清單
6. 整理成每週、故障時、改版後三種維護流程
7. 補上驗收條件與回歸檢查項

## Validation

- `plans/youtube-update-maintenance/` 內每份文件都符合 planner skill 的必要結構。
- SOP 能對應到具體檔案，且每個更新點都有明確檢查方式。
- 後續任一位維護者可依文件完成一次完整診斷，不必依賴口頭背景。

## Handoff

- Build agent must read this spec first.
- Build agent must read proposal.md / spec.md / design.md / tasks.md / handoff.md before coding.
- Build agent must materialize tasks.md into runtime todos before coding.
- Build agent must treat this package as the active maintenance contract for YouTube-related updates.

