# BR: `DELETE /api/downloads/{job_id}` 對不存在的 job 回 200 且宣稱「已刪除」

**Filed**: 2026-08-09
**Status**: FIXED-UNCOMMITTED（修復已在工作樹，與解耦 `purge` 同一次變更；commit 授權在 dispatcher）
**Severity**: MEDIUM — 本身不造成資料損失，但**讓其他缺陷的歸因變得極其困難**，實測已造成一次
**Owner**: unassigned
**Related**:
- `BR_20260809_delete_endpoint_couples_list_removal_with_file_deletion.md`（**同一個端點的另一個缺陷**，同族：那張是「刪清單順便刪檔」，這張是「什麼都沒刪也說刪了」；兩者都源於端點對自己實際做了什麼不做回報）
- `BR_20260809_disk_rescan_marked_history_completed_and_autosave_deleted_73_files.md`（**本缺陷是該事故歸因困難的直接原因**：37 次重複刪除在 log 上與真實刪除逐字同形，無法從 log 分辨，只能靠比對 `DELuniq` 與 `DEL` 才發現）

## 缺陷

```python
# queue_manager.py:134（修復前）
def clear_job(self, job_id):
    if job_id in self.jobs:      # ← 它知道自己什麼都沒做
        ...
        del self.jobs[job_id]
    # 沒有 else，沒有回傳值

# main.py:1194（修復前）
@app.delete("/api/downloads/{job_id}")
async def cancel_download(job_id: str):
    queue_manager.cancel_job(job_id)
    queue_manager.clear_job(job_id)
    return {"status": "deleted"}   # ← 無條件宣稱已刪除
```

**「刪除成功」與「這個資源根本不存在」共用同一個輸出。** 而且比單純沒有訊號更糟——它**主動發出了錯誤訊號**：回應文字明說 `"deleted"`，而實際上可能一個 byte 都沒動。

`clear_job` 的第一行就是 `if job_id in self.jobs`，**那一格資訊系統當下有沒有？有**。它知道答案，只是不說。

## 實測代價（不是假設，已發生）

2026-08-09 的刪檔事故中，log 有 112 次 DELETE 但只有 75 個 distinct job_id ——**37 次是同一個 job 被刪第二次**。

```
DELETE 呼叫數        112
distinct job_id       75
重複呼叫              37   ← 全部回 200 {"status": "deleted"}
```

第二次刪除時 job 已從 `self.jobs` 移除、檔案已不存在，`clear_job` 直接落到函式尾端什麼也沒做，端點照樣回 `200 {"status": "deleted"}`。**在 log 上，這 37 次與 75 次真實刪除逐字同形。**

歸因時無法從 log 判斷「112 次刪除」是刪了 112 個檔還是 75 個檔，只能靠 `distinct` 比對才發現差額。**若當時磁碟上恰好有 112 個檔，這個差額會完全隱形。**

（重複刪除本身的成因是另一件事：`activeAutoSaves` 在 `finally` 移除 job，而前端每 2 秒輪詢，若 DELETE 尚未反映在下一次回傳中，該 job 會再次通過 `readyJobs` filter。那是前端競態，不在本 BR 範圍。）

## 判別力證明（本 BR 的控制組）

指控「`DEL_without_GET = 0`」這種**缺席宣稱，沒有控制組就不是證據**。做法是往 log 尾端塞一筆 job_id 從未出現在任何 GET 的 DELETE，證明偵測器真的會回非零：

```
                       GETuniq  DEL  DELuniq  DEL_without_GET  dup_jobs  extra_calls
REAL                     75     112     75           0            37        37
CONTROL(+1 orphan)       75     113     76           1            37        37
VERDICT: detector has power = True（控制組必須恰為 real+1，實測相符）
```

同一手法可用於驗證本 BR 的修復：修復後對不存在的 job_id 發 DELETE，**回應必須與真實刪除不同**。

## 修復（已在工作樹）

`clear_job` 改為回傳結構而非 `None`，端點依實際結果回報：

```python
def clear_job(self, job_id, purge=False):
    if job_id not in self.jobs:
        return {'removed': False, 'purged': False, 'file': None, 'error': None}
    ...
    return {'removed': True, 'purged': purged, 'file': fpath, 'error': error}
```

```python
if not result['removed']:
    return {"status": "not_found", "removed": False, "purged": False}
return {"status": "purged" if result['purged'] else "removed_from_list", ...}
```

三個狀態現在**互不相同**：`not_found` / `removed_from_list` / `purged`。

驗證（容器內實跑，四組對照）：

```
G1 default（purge 省略）  removed=True  purged=False  file_exists=True   ← 預設不刪檔
G2 purge=True             removed=True  purged=True   file_exists=False
G3 job 不存在             removed=False purged=False                     ← 不再冒認已刪
G4 purge=True 但檔已消失  removed=True  purged=False  error=None         ← 不冒認已 purge
BACKEND_FAILURES=0
```

**G3 與 G4 各自封住一個「冒認」**：G3 是冒認刪了不存在的 job，G4 是冒認 purge 了不存在的檔。

## 未量測

- **未量測前端是否有任何呼叫端依賴舊的 `{"status": "deleted"}` 字串**。目前所有前端呼叫點都不讀回應 body（只 `await fetch(...)` 後 `fetchDownloads()`），故研判無回歸，但**未逐一驗證每個呼叫端的回應處理**。
- 未量測 37 次重複刪除的精確競態窗口（無 client-side timing）。
- `cancel_job` 對**進行中**的 job 是否真能中止 yt-dlp 仍未驗——它只設 `status='cancelled'`，而 `_worker` 只在迴圈開頭檢查，已在下載中的不會被打斷。相鄰但獨立的一格。

**Closed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（dispatcher 獨立驗證 + live 生效確認）
