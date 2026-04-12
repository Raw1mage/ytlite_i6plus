# Handoff

## Execution Contract

- Build agent must read implementation-spec.md first
- Build agent must read proposal.md / spec.md / design.md / tasks.md before coding
- Materialize tasks.md into runtime todos before coding
- This plan package is the active source for YouTube-related maintenance updates

## Required Reads

- implementation-spec.md
- proposal.md
- spec.md
- design.md
- tasks.md

## Current State

- 已完成盤點與 RCA。
- 根因：yt-dlp 未固定版本（過舊）、Invidious image 用 `latest` 未重建。
- 計畫已從「僅建 SOP」升級為「建 SOP + 實施最小修復」。
- **Phase 1（最小修復）** 已定義，可直接執行。

## Stop Gates In Force

- 如果 yt-dlp `2026.3.17` build 失敗，必須檢查是否有相容性問題再換版本。
- 如果 Invidious 固定版本後啟動失敗，必須檢查 DB migration 相容性。
- 如果修復後仍無法播放，必須回到 plan 再拆下一輪任務（可能需改 runtime）。

## Build Entry Recommendation

- 從 tasks.md Phase 1（依賴升級）開始。
- 修改兩個檔案 → 重建容器 → 驗證。
- Phase 1 完成後再進入 Phase 2（SOP 文件化）。

## Execution-Ready Checklist

- [x] Implementation spec is complete
- [x] RCA is documented in proposal.md and design.md
- [x] Companion artifacts are aligned
- [x] Validation plan is explicit (spec.md acceptance checks)
- [x] Runtime todo seed is present in tasks.md
- [x] Fix targets are concrete (2 files, specific versions)
