# 系統架構分析與文件同步 (Architecture Sync)

## 需求
依據全域開發準則 `AGENTS.md` 規範，對專案 codebase 進行架構分析，並全面重寫 `docs/ARCHITECTURE.md`，使之能反映最新的現狀（含 Invidious、FastAPI 中介層、以及近期加入的下載器 Queue Manager 等機制）。

## 範圍 (IN/OUT)
- **IN**: FastAPI API endpoints、Invidious proxy、yt-dlp 下載器與快取機制、OAuth2、容器化結構 (Docker Compose)。
- **IN**: 撰寫最新版的 `ARCHITECTURE.md`，使用 `mermaid` 語法畫出現行架構與資料流。
- **OUT**: 大規模重構程式碼（僅限於文件更新）。

## 任務清單
- [x] 分析 `webbox/src/middleware/main.py` 與路由結構。
- [x] 分析 `queue_manager.py` 與 `downloader.py` 的下載/快取管線。
- [x] 確認 Docker compose 的容器名稱更動 (webbox -> ytlite) 與對應的服務拓墣。
- [x] 根據現況撰寫 `docs/ARCHITECTURE.md` (全貌同步)。

## Debug Checkpoints 
- *Baseline*: `ARCHITECTURE.md` 未包含 `downloader` 下載佇列模組，且 `docker-compose.yml` 容器命名與描述未能與最新現狀完全匹配。
- *Execution*: 分析了 `main.py`、`queue_manager.py` 與 `downloader.py`，發現架構中包含一條新的背景下載與快取管線，儲存於 `/app/data/downloads` 與 `/app/data/cache`。
- *Validation*: 已成功將分析結果整合並寫入 `docs/ARCHITECTURE.md`，符合 `Architecture Sync: Verified (Doc changes applied)` 的結算門檻。
