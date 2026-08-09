# BR: 把歷史檔標成 `completed` 讓既有 auto-save 管線刪掉了 73 個使用者檔案

**Filed**: 2026-08-09
**Status**: CLOSED — 方向 1（狀態分離 `archived`）已實作、dispatcher 獨立驗證、live 生效（`204b2ff`）；前置的 DELETE 解耦先行落地（`928202e`）。使用者已就資料損失做出裁示（見下方「使用者裁示」），淨損失那格不再是待辦。方向 3 已拆為獨立 BR 追蹤，不隨本張一起埋掉
**Severity**: CRITICAL — 已造成實際資料刪除（73 檔 / 原記錄約 4.6 GB）
**Owner**: coordinator `ses_01b36b5ffffeNy0N6OCtYnJm5n`（我授權了這個 commit，歸責在我）
**Related**:
- `BR_20260809_download_jobs_in_memory_only_vanish_on_restart.md`（**因果直系**：本事故正是執行該 BR「建議修法方案 1」的結果。該 BR 的方案 1 現已證明有害，須加警告）
- `BR_20260809_delete_endpoint_couples_list_removal_with_file_deletion.md`（同一條 kill chain 的下游：`DELETE` 端點把「移出清單」與「`os.remove`」耦合。若那格已解耦，本事故只會清空清單而不會刪檔）
- `BR_20260809_touch_devices_can_never_enter_selection_mode.md`（同一輪修復包的姊妹缺陷，無因果關係）

## 一句話

`rescan_download_dir()` 把磁碟上 73 個歷史檔案標成 `status='completed'`，而 `completed` 在這個系統裡的**既有語意是「剛下載完、待存本地、存完可從伺服器刪除」**——於是前端的 auto-save 輪詢把它們逐個存到使用者本地後 `DELETE`，`clear_job()` 執行 `os.remove()`，磁碟被清空到只剩 2 個 `.part`。

## 損害與緩解（已量測，非推論）

```
目錄檔案數：75 → 38 → 15 → 6 → 4 → 2（穩定）
倖存者：僅兩個 .part（rescan 刻意排除的 partial 檔）
        40cc193a-….f399.mp4.part   (300 MB)
        5bad0351-….f137.mp4.part   (20 MB)
```

**關鍵緩解事實**：被刪的檔案**全部**先被成功傳輸給使用者的瀏覽器了。

```
distinct_deleted            = 75
distinct_fetched            = 75
deleted_but_NEVER_fetched   = 0     ← 沒有任何檔在未被取走的情況下被刪
fetched_but_not_deleted     = 0     ← 兩個集合完全相同
GET /api/download_file/ 狀態碼：75×200, 8×404
```

silent-save 分支是「`await writable.close()` 成功才回 `'confirmed'`」，故那 75 個檔極可能已落在使用者桌機那個授權過的下載資料夾中。**實際淨損失需使用者確認本地資料夾後才能定案；未經確認前一律視為已損失。**

## 歸因（決定性）

被刪 job_id 的 UUID 版本分佈：

```
DELETE /api/downloads/<id> 共 112 次（重啟前僅 2 次），distinct=75
  第 3 組首字 '5'（uuid5）→ 110
  第 3 組首字 '4'（uuid4）→   2

控制組（容器內實跑同一 namespace）：
  uuid.uuid5(_DISK_JOB_NS, path) → 620d6138-9646-5691-…   ← 第 3 組首字 5
  uuid.uuid4()                   → 29807ae6-281b-4322-…   ← 第 3 組首字 4
```

`uuid5` 在本 repo **只有一個產生者**：`b29dd09` 新增的 `rescan_download_dir()`。既有 `add_job()` 用 `uuid4`。故那 110 次 version-5 的 DELETE 全部作用在 rescan 產生的 job 上。

## Kill chain

```
容器重啟
  → rescan 掃出 73 個歷史檔，硬寫 status='completed'、is_cache=False（queue_manager.py:126）
  → /api/downloads 回 73 筆（main.py:1177 的 is_cache 過濾全部放行）
  → 使用者桌機 Chrome 持有 downloadDirHandle，fetchDownloads 每 2 秒輪詢
  → base.html:2745  readyJobs = jobs.filter(j => j.status === 'completed')
  → 對 73 筆逐個 autoSaveJob()
  → silent 分支「真的成功」寫入本地 → 合法回 'confirmed'
  → DELETE /api/downloads/<id> → clear_job() → os.remove(fpath)   ×73
```

## 為什麼同一輪的止血刀救不到（這一格最值得記）

同一個修復包裡的 `adbdd5d`（「未確認本地存檔前不得刪除伺服器副本」）在此**完全無效，而且它的守衛是正確運作的**：

- 止血刀防的是「**不知道有沒有存到卻謊報成功**」（iframe fallback 無條件 `return true`）
- 本事故是「**確實存到了，但這個動作根本不該在此刻發生**」

silent 分支真的寫入成功，所以它合法回 `'confirmed'`，呼叫端合法刪除。**每一步都符合新加的守衛。** 這是兩個不同的缺陷，同一輪只看見了前者。

**通則**：「動作的前提是否成立」與「動作是否該被觸發」是兩個正交的閘。補上前者不會覆蓋後者，而兩者的成功輸出長得一樣。

## 我的判斷失誤（歸責在 coordinator，不在 handler）

我把 `b29dd09` 當成「純新增、無破壞性」並授權 commit，理由是它只讀磁碟、只往 `self.jobs` 加東西。**那個推理漏了一整層**：`self.jobs` 不是私有狀態，它經 `/api/downloads` 餵給一個**會依 `status` 自動採取破壞性動作的前端**。

我獨立驗證了 rescan 本身（三組對照 + 突變控制組全綠，數字 73 = 75 檔 − 2 partial 也對得上），**卻沒有問「多出 73 筆 completed job 之後，系統會拿它們做什麼」**。B 的測試套件全綠而生產環境刪光檔案，兩者不矛盾——**測的是函式，不是它注入的那個迴圈**。

這是 §8.1.4 的選點塌縮：所有 mutation 都打在 rescan 的內部行為上，沒有一刀打在「它的輸出被誰消費」。**至少一刀要打在資料流的下游消費端，不只打在產生端。**

## 復發風險（revert 前）

`os.remove` 是真刪、無回收桶。而**這個迴圈會在每次 middleware 重啟時重演**：目前只因目錄已空而停止。使用者一旦重新下載，下次重啟就再刪一輪。

## 已做的處置

```
git revert --no-edit b29dd09   →  dacbe50（僅 queue_manager.py，1 insertion / 111 deletions）
docker restart ytlite          →  Pid 1322 → 4914

驗證（含控制組）：
  [Queue] rescan log      0 次    控制組 'Application startup complete' 1 次 ← 讀的是新啟動的 log
  /api/downloads          200, count=0   ← 不再注入 completed job
  目錄檔案數              2，穩定不再下降
  A + 止血刀仍在 live     select-mode-btn=3, window.selectionMode=9, 'unknown'=1（控制組 0）
```

`1763bd9`（A 觸控選取）與 `adbdd5d`（止血刀）**未受影響、未 revert、仍有價值**。

## 根本修法（方向 1 已做並生效 2026-08-09；三個方向）

判別點是「rescan 產生的 job 該不該進 auto-save 管線」——答案是不該。

1. **狀態分離**：rescan 用新狀態 `'archived'` 而非 `'completed'`。前端 `readyJobs` 只收 `completed`/`finished`，`archived` 自然被排除但仍渲染。**改動最小、語意最誠實**——它本來就不是「剛完成」。
2. **旗標排除**：保留 `completed`，靠 `from_disk: True` 在 `base.html:2745` 與 `downloads.html` 對應處排除。**不建議單獨採用**：依賴前端每一處都記得檢查，漏一處就再刪一輪。
3. **auto-save 只認本 session 發起的下載**：語意最正確（auto-save 本意是「我剛叫它下載的東西存好就清掉」），改動面最大。

**1 + 3 才閉環**，1 可立即止血。

> **2026-08-09 進度**：方向 1 已實作於 `204b2ff`（`ARCHIVED_STATUS='archived'`），
> 前置的 DELETE 解耦已於 `928202e` 落地。dispatcher 獨立驗證含：突變打在常數源碼行、
> 打在 `__init__` 的 rescan 呼叫點（接線那格）、七個前端 status filter 全數確認排除 archived
> 且各自 mutant 皆放行。live 端到端：種檔 → restart → `1 archived job(s) restored` →
> API `status='archived'` → `GET /api/download_file` 200 精確位元組 → `purge=false` 檔存活 →
> restart 後同一 uuid5 → `purge=true` 移除。**方向 3（auto-save 只認本 session）仍未做**，
> 故閉環未完成；目前的安全性質靠七個 filter 不含 archived 維持。**任何重做 rescan 的嘗試都必須先解耦 `DELETE`**（見 Related 第二條），否則同一條 kill chain 仍然存在，只是等下一個觸發者。

## 對既有 BR 的影響

`BR_20260809_download_jobs_in_memory_only_vanish_on_restart.md` 的「建議修法方案 1」（掃描目錄建 `status='completed'` 的 job）**已證明會刪除使用者資料**。該 BR 必須加註警告，否則下一個讀者會照著再做一次——**一張讀起來像現況的 BR，其建議修法可以是已被證否的**。

## 未量測

- **使用者本地資料夾是否真有那 75 個檔**——無 client-side 可視範圍，需使用者自行確認
- **112 次 DELETE 與 75 個 distinct id 的差額（37 次重複）未歸因**——可能來自 `clearFinished` 批次 `Promise.all`，或輪詢競態重複發送
- **8 次 `download_file` 回 404 未歸因**——可能是已被刪除後的重試
- **未在刪除前重新量測總大小**（先前記錄 4.6 GB，未於事故當下複測）

---

## 使用者裁示（2026-08-09）

問：73 個檔在被刪前每一個都先成功傳到桌機 Chrome 的授權資料夾（75 次 `download_file` 全 200、
`deleted_but_NEVER_fetched = 0`），是否去確認過那個資料夾、淨損失是接近零還是 4.3 GB？

答：**「忽略舊檔。我不再需要他們。」**

**這句話的邊界必須寫清楚，因為它極容易被下一個讀者讀寬**：

- 使用者放棄的是**那 73 個已經不存在的檔**，以及追查它們下落這件事。
- 使用者**沒有**同意「未來可以再刪一次」。他先前對歷史檔的說法一直是「不備份、不怕丟」，
  而本事故的問題從來不是「檔案可能丟」，是**一個新改動主動刪光了它們**。這兩件事不同。
- 因此本 BR 的所有防護（狀態分離、DELETE 解耦、七個 filter 不含 `archived`）
  **一格都不因這句裁示而放寬**。

## 方向 3 的去向

原「根本修法」列的三個方向裡，**方向 3（auto-save 只認本 session 發起的下載）仍未做**。
它不隨本張歸檔而消失，已拆出獨立追蹤：

`BR_20260809_autosave_uses_exclusion_list_not_allowlist_to_decide_deletion.md`

拆出的理由：方向 1 已經阻斷事故，方向 3 是**防禦深度**——它要修的不是任何現存 bug，
而是「排除式判準讓所有未來的新狀態預設會被自動刪」這個結構條件。
把它留在一張 CLOSED 的事故 BR 內文裡，等於讓它消失。

**Closed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（方向 1 已 live 生效並獨立驗證；使用者裁示放棄舊檔；方向 3 已獨立建檔）
