# Gemini 開發守則（繁體）

## 專案背景
目標：為越獄的 iPhone 6 Plus（iOS 12）提供自架、輕量的 YouTube 客戶端「YT Lite」。裝置透過 Safari WebClip 充當前端，後端/中介層在 PC/WSL 運行（Flask/FastAPI + yt-dlp/Invidious）。

## 文件標準（重要）
所有開發活動一律記錄在 repo 的 `docs/` 目錄。

### 1. `docs/PROGRESS.md`
- **用途**：追蹤功能與任務狀態。
- **頻率**：完成一個階段或重大任務後更新。
- **格式**：分階段標題，使用核取方塊 `[ ]` / `[x]`。

### 2. `docs/DEBUGLOG.md`
- **用途**：問題知識庫。
- **何時記錄**：
  - 任一 bug 需要多次嘗試修復。
  - 安裝/環境問題（特別是 iOS/JB 特有狀況）。
  - 即使未解決、放棄的嘗試也要寫下來，避免重複踩雷。
- **結構**：
  - 日期 `[YYYY-MM-DD]`
  - 問題 / 症狀 / 根因 / 解法或嘗試結果

### 3. `docs/README.md`
- **用途**：文件入口。
- **內容**：架構、安裝、使用方式與其他文件連結。

## 作業流程
1. **主要程式位置**：現階段主力在 PC/WSL `webbox`；若於手機端維護，放在 `/var/mobile/Documents/yt_lite` 並確保 Git 追蹤。
2. **版本控管**：所有變更都以 Git 管理，保持 commit 清晰。
3. **遠端控制**：透過 SSH 操作裝置；如需 root 權限，先確認安全性。

## 環境限制
- **裝置**：iPhone 6 Plus（A8，1GB RAM）
- **OS**：iOS 12.5.7
- **Python**：3.9.x
- **編譯器**：無可用 C 編譯器，盡量選用純 Python 套件或預編譯 wheel。
