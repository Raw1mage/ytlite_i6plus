# 舊版開發計畫歸檔 (Historical Plans Archival)

## 需求
根據系統現況分析，發現專案根目錄下的 `docs/PLAN.md`（紀錄 2025/12 期間的 MVP 進度與 Roadmap）以及 `docs/PLAN_DOWNLOAD.md`（設計了下載功能的規格），皆為已經「實作完成且不再被作為即時追蹤對象」的過時文件。
為符合 `AGENTS.md` (已同步至 `GEMINI.md`) 的統一歷史追蹤原則，必須將這些計畫也轉存至 `docs/events/` 下，完成徹底的文件整併。

## 範圍 (IN/OUT)
- **IN**:
  - `docs/PLAN.md` -> 移至 `docs/events/event_20251216_v3_roadmap_plan.md`
  - `docs/PLAN_DOWNLOAD.md` -> 移至 `docs/events/event_20260117_download_feature_plan.md`
- **IN**: 更新專案根目錄的 `README.md`，移除失效的 `PLAN` 參照，讓未來的所有計畫紀錄都在單一入口 `docs/events/` 查詢。
- **OUT**: 刪除計畫文件（以存檔方式保留，不會刪除歷史想法）。

## 任務清單
- [x] 將舊計畫檔搬移並按日期重命名。
- [x] `README.md` 的文件導覽更新。

## Debug Checkpoints
- *Baseline*: `docs/` 下殘留有兩份已經被實踐的過時 `.md` 計畫檔，造成文件權威度下降。
- *Execution*: 將 `PLAN` 文件轉存為歷史 Event 記錄，不再作為開發中的活躍狀態指標；從 `README.md` 剝離了直接指向 `PLAN.md` 的捷徑。
- *Validation*: 這些檔案不再散落於 `docs/` 第一層，專案將改採 `event_檔先行` 方式規劃新功能。 `Architecture Sync: Verified (No doc changes needed for root)`。
