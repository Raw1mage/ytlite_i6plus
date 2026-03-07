# 老舊歷史追蹤與除錯紀錄轉移 (Historic Logs Migration)

## 需求
根據 `AGENTS.md` (已同步至 `GEMINI.md`) 中全新的文件維護指南，所有的 `CHANGELOG.md`、`DEBUGLOG.md`、以及 `HISTORY` 相關內容需全數轉移至 `/docs/events/` 結構之下，並以統一的日期與事件格式管理。

## 範圍 (IN/OUT)
- **IN**:
  - `CHANGELOG.md` -> `event_20260120_historical_changelog.md`
  - `DEBUGLOG.md` -> `event_20260120_open_file_explorer_debug.md`
  - `docs/DEBUGLOG.md` -> `event_20260118_past_debug_logs.md`
  - `docs/HISTORY/DEBUG_LOG.md` 以及其附屬檔 (`json` 檔與 `legacy_code`) -> 分別更名/放至於對應的 `event_*` 與 `legacy_code_archive` 中。
  - `docs/HISTORY/PROGRESS.md` -> `event_20251214_v1_v2_progress.md`
- **IN**: 更新專案根目錄的 `README.md`，將文件導覽指向最新的 `docs/events/` 資料夾，並移除遺留的路徑。
- **OUT**: 修改上述文件的任何實質原始文本內容。

## 任務清單
- [x] 清查專案下的老舊 Log。
- [x] 將舊文件 `mv` 到 `docs/events/` 底下並以新的 `event_<YYYYMMDD>_<topic>.md` 規則重新命名。
- [x] 成功將 `docs/HISTORY` 移除。
- [x] 同步更新 `README.md`，使文件導向指向新結構。

## Debug Checkpoints
- *Baseline*: `README.md` 的「文件導覽」仍指向 `CHANGELOG.md`、`docs/DEBUGLOG.md` 與 `docs/HISTORY/`，且所有舊文件格式均未依照新版 event guideline。
- *Execution*: 將這 6 份實體檔案移入 `/events/`。`docs/DEBUGLOG.md` 等被完整保留其內文以供往後追溯除錯脈絡。修改了 `README.md` 中的文件維護指南。
- *Validation*: 使用 `git status` 檢查，確認變更皆被記錄在 untracked `docs/events/` 狀態以及 modification state，路徑清理乾淨。 `Architecture Sync: Verified (No doc changes)`。
