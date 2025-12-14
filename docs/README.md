# 文件索引（繁體）

此目錄為 YT Lite v3 的主要文件入口。

## 你會在這裡找到
- **系統架構**：`../ARCHITECTURE.md`
- **開發計畫**：`PLAN.md`
- **進度摘要**：`PROGRESS.md`
- **除錯紀錄（精簡版）**：`DEBUGLOG.md`
- **歷史記錄**：`HISTORY/`（包含完整除錯與舊版進度）
- **作業準則**：`../gemini.md`

## 快速背景
- 目標：為 iPhone 6 Plus（iOS 12）提供輕量、無廣告、繁中優先的 YouTube 介面。
- 架構：iOS Safari 客戶端 ←→ FastAPI 中介層（1214） ←→ Invidious（1215）+ Postgres（1216），可選 Nginx/HTTPS。
- 播放策略：以 YouTube iframe 為主，減少直抓串流失敗。

## 如何更新文件
- 計畫/進度：更新 `PLAN.md`、`PROGRESS.md`，維持核對清單與日期。
- 除錯：新增條目到 `DEBUGLOG.md`，詳細長文放 `HISTORY/DEBUG_LOG.md`。
- 若有重大架構或流程變更，務必同步調整 `../README.md` 與 `../ARCHITECTURE.md`。
