# 專案目錄結構清理 (Scripts & Logs Consolidation)

## 需求
依據系統最新維護指南與使用者指令，將專案目錄下散落的工具腳本集中移至 `/scripts`，並將雜亂的日誌檔案統一收合於 `/logs` 資料夾下，還給專案根目錄乾淨的結構。

## 範圍 (IN/OUT)
- **IN**:
  - `browser_preview.sh` -> `scripts/browser_preview.sh`
  - `watcher.sh` -> `scripts/watcher.sh`
  - `webbox/webctl.sh` -> `scripts/webctl.sh`
  - `watcher.log` -> `logs/watcher.log`
  - `.chrome_preview.log` -> `logs/chrome_preview.log`
  - `webbox/run.sh` -> `docs/events/legacy_code_archive/run.sh` (不再維護的舊版 Python 啟動腳本，歸檔)
- **IN**: 更新腳本內部的相對路徑引用，確保腳本在移動後功能依然正常運作。
- **OUT**: 大規模修改程式架構，或變更既有 Docker 配置。

## 任務清單
- [x] 建立 `scripts/` 與 `logs/` 目錄。
- [x] 移動工具文件與除錯日誌檔。
- [x] `scripts/browser_preview.sh`：修改 `$LOG_FILE` 輸出路徑指向 `../logs/chrome_preview.log`。
- [x] `scripts/webctl.sh`：在腳本開頭加入 `cd "$(dirname "$0")/../webbox"`，確保 `docker-compose.yml` 可以正確解析出內部的 `./src/...` 映射路徑。


## Debug Checkpoints
- *Baseline*: `webbox/webctl.sh`、`watcher.sh`、`browser_preview.sh` 散佈於根目錄與子目錄中；Log 出現隱藏檔如 `.chrome_preview.log`。
- *Execution*: 使用 mv 統一分類，並對兩個具有路徑依賴的腳本使用動態相對路徑解析 `$(dirname "$0")` 確保移動位置的無縫銜接。舊版的 `webbox/run.sh` 因不再需要則移至遺產封存區。
- *Validation*: 腳本皆能正確找到目標。 `Architecture Sync: Verified (No doc changes)`。
