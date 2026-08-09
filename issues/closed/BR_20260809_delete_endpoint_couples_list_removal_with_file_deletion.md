# BR: `DELETE /api/downloads/{id}` 把「移出清單」與「刪實體檔」綁成同一個動作

**Filed**: 2026-08-09
**Status**: OPEN
**Severity**: MEDIUM — 不會造成資料靜默遺失（已由 adbdd5d 止血），但使用者只想整理清單時仍會失去檔案
**Owner**: unassigned
**Related**: `BR_20260809_download_jobs_in_memory_only_vanish_on_restart.md`（同一族：兩者相加才真正閉環，見下方「為什麼要一起看」）

## 現況

`main.py:1190-1193`：

```python
@app.delete("/api/downloads/{job_id}")
async def cancel_download(job_id: str):
    queue_manager.cancel_job(job_id)
    queue_manager.clear_job(job_id)
    return {"status": "deleted"}
```

`queue_manager.py` 的 `clear_job` 會 `os.remove(fpath)` —— **這不是只從清單移除，是真的刪檔**。

而 UI 上有三個入口打同一個端點，語意其實不同（行號為 adbdd5d 後）：

| 入口 | 函式 | 使用者的意圖 |
|---|---|---|
| 取消進行中的任務 | `cancelJob` | 停止下載，刪暫存檔**合理** |
| 刪除單筆 | `deleteJob` | 未必想刪檔，可能只想清列表 |
| 清除所有已完成 | `clearFinishedDownloads` / `clearFinished` | **多半只是想清列表** |

第三個尤其危險：文案寫「確定要清除所有已完成的任務嗎？(檔案將被刪除)」，但「清除已完成任務」這個動作在絕大多數下載管理器裡都只是清列表。

## 提案

`DELETE /api/downloads/{id}?purge=<bool>`，**預設 `purge=false`**（僅移出清單，不動檔案）：

- `cancelJob`（進行中）→ `purge=true`
- `deleteJob` / `clearFinished`（已完成）→ 預設 `purge=false`，另給明確的「刪除檔案」動作

## 為什麼要和 rescan 一起看

單獨做這個提案只解一半。配合 `b29dd09` 的 `rescan_download_dir()`（磁碟為 SSOT，啟動時從 `download_dir` 重建 job）：

- 誤清列表 → 重啟後從磁碟還原，**可恢復**
- 真的要刪檔 → `purge=true`，明確且不可逆

**兩者相加才真正閉環**：一個保證「清單可重建」，一個保證「不會誤刪來源」。只做前者，使用者仍會因為按了「清除」而永久失去檔案；只做後者，清單一重啟就空。

## 為什麼這一輪不做

這是**行為變更**不是缺陷修復。使用者當下最需要的是止血（已由 `adbdd5d` 完成：未確認落地的路徑不再觸發 DELETE）。改變 DELETE 的預設語意需要同時調整前端三個呼叫點與文案，且會改變既有使用者的肌肉記憶，應獨立評估。

## 未量測

- 未量測既有 75 個檔中有多少是被「清除已完成」誤刪剩下的——無歷史 log 可比對。
- 未確認 `cancel_job` 對**進行中**的 job 是否真能中止 yt-dlp（它只設 `status='cancelled'`，worker 在 `_worker` 迴圈開頭才檢查，已在下載中的不會被打斷）。這是相鄰但獨立的一格。

**Closed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（dispatcher 獨立驗證 + live 生效確認）
