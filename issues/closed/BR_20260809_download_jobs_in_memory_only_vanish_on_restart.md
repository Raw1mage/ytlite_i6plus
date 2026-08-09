# BR: 下載紀錄只存在記憶體，容器一重啟就全部蒸發，UI 永遠是空的

**Filed**: 2026-08-09
**Status**: FIXED（`204b2ff`，已 live 生效）— ⚠ **但下方「建議修法方案 1」的原始寫法仍是有害的，不得照做**。實際採用的是它的修正版：狀態寫 `'archived'` 而非 `'completed'`，且前置解耦 `DELETE`（`928202e`）。差別只有一個字串，後果是 73 個檔案
**Severity**: HIGH — 這是「使用者看不到檔案下載功能」的頭號成因
**Owner**: unassigned
**Related**:
- `BR_20260809_root_owned_dirs_in_repo_from_root_container_bind_mount.md`（同一個 `/opt/ytlite_v3/user_db` 掛載點；該 BR 談權限，本 BR 談狀態持久化）
- `BR_20260809_disk_rescan_marked_history_completed_and_autosave_deleted_73_files.md`（**因果直系**：執行本 BR 方案 1 的實作 `b29dd09` 刪掉了 73 個使用者檔案，已 revert）

---

## ⚠⚠ 警告：本 BR 的「建議修法方案 1」已被證否（2026-08-09 同日實測）

方案 1（掃描 `download_dir`，為既有檔案建立 `status='completed'` 的 job）**已實作、已上線、已刪除 73 個使用者檔案**，肇事 commit `b29dd09` 已 revert 為 `dacbe50`。

**為什麼**：`completed` 在本系統的既有語意是「剛下載完、待存本地、存完可從伺服器刪除」。前端 auto-save 輪詢（`base.html:2745` 的 `readyJobs` filter）會把每一筆 `completed` 存到使用者本地後 `DELETE`，而 `DELETE` 端點呼叫 `clear_job()` → `os.remove()`。

**若要重做，必讀** `BR_20260809_disk_rescan_marked_history_completed_and_autosave_deleted_73_files.md` 的「根本修法」段（狀態分離為 `'archived'` + auto-save 只認本 session 發起的下載），且**必須先解耦 `DELETE` 端點**（`BR_20260809_delete_endpoint_couples_list_removal_with_file_deletion.md`），否則同一條 kill chain 只是換一個觸發者。

---

## 症狀

使用者回報「看不到檔案下載功能」。功能在 code 裡完整存在、按鈕也在 DOM 裡，但**下載管理員打開後是空的**。

## 根因

`webbox/src/middleware/queue_manager.py:24` —

```python
self.jobs = {}   # { job_id: { ... } }
```

`QueueManager.jobs` 是**純記憶體 dict**，沒有任何持久化：

- `add_job()` 寫進 dict
- `get_jobs()` 從 dict 讀
- 沒有寫檔、沒有讀檔、沒有 DB

`main.py:1173` 的 `/api/downloads` 直接回 `queue_manager.get_jobs()`。

**middleware 容器今天重啟過**（commit `7eb084b` 生效）。重啟 ⇒ `jobs = {}` ⇒ `/api/downloads` 回 `[]` ⇒ 下載管理員空白。

## 第二層：磁碟上有檔案，但沒有任何程式碼會去看它

```
/opt/ytlite_v3/user_db/downloads/  →  4.6 GB、75 個 .mp4/.mp3（Jan 18 2026 ~ Apr 12 2026）
```

檔案**一直都在**。但 `QueueManager` 啟動時**不掃描 `download_dir`**，也不從檔名重建索引。`__init__` 只做 `os.makedirs`。

所以這不是「下載壞掉」，是 **UI 與磁碟之間唯一的索引存在記憶體裡，而那份索引在每次重啟時被清空**。使用者的 4.6 GB 檔案在 UI 上是不可見的。

`os.path.exists(target_path)` 那條快取路徑（`queue_manager.py:66`）證實了設計者知道檔案會留下——但只有在**使用者重新下載同一支影片**時才會發現它，而且才會產生一筆 job。沒有任何路徑會主動列出既有檔案。

## 證據

全部已實跑，非推導：

```bash
# jobs 無持久化：整份 queue_manager.py 沒有任何寫檔/讀檔
grep -cE "json\.dump|json\.load|open\(|pickle|sqlite|\.write\(" queue_manager.py
# → 0   (rc=1)
# 正控制組（證明同一條 grep 會命中）：
grep -cE "os\." queue_manager.py
# → 21  (rc=0)
# 負控制組（證明 0 不是恆定輸出）：
grep -cE "ZZZNOSUCHTOKEN" queue_manager.py
# → 0   (rc=1)

# downloader.py 也無持久化
grep -cE "json\.dump|sqlite" downloader.py            # → 0
# main.py 無任何 jobs 存續處理
grep -nE "queue_manager\.(jobs|load|save)|jobs\.json" main.py   # → 無匹配 (rc=1)

# 磁碟上確實有檔案
ls -1 /opt/ytlite_v3/user_db/downloads/ | wc -l   # → 75

# log 裡 /api/download* 出現次數
grep -c '/api/download' <container log>   # → 0  (rc=1)
# 正控制組：
grep -c '/api/videos' <container log>     # → 9  (rc=0)
```

log 中 `/api/download*` **零次**、`/api/videos` 九次，代表使用者這段期間**從未成功發出下載請求**——與「打開管理員發現是空的就放棄」的行為一致。

## 建議修法（三選一，遞增）

1. ~~**最小**：`QueueManager.__init__` 掃描 `download_dir`，為每個既有檔案建立 `status='completed'` 的 job（video_id 從檔名 stem 取）。一次修好「重啟後空白」＋「歷史檔案不可見」。~~ **← 已證否，會刪光使用者檔案，見本檔開頭警告。** 掃描目錄本身是對的，錯的是把結果標成 `completed`。
2. **中等**：`jobs` 落 JSON 到 `DATA_DIR/jobs.json`，每次異動寫回；啟動時載入並與磁碟現況對帳（檔案不存在的 job 標記為 missing）。
3. **完整**：改用 SQLite（`DATA_DIR` 已是持久化 volume），job 表 + 啟動時 reconcile。

~~方案 1 應優先~~，因為它讓**磁碟成為 SSOT**，而不是再加一份會與磁碟不同步的側錄。**「磁碟為 SSOT」這個方向仍然正確**，被證否的只是「用 `completed` 這個狀態去表達它」——那個狀態已經被前端賦予了破壞性語意。改用不觸發 auto-save 的新狀態（如 `'archived'`）才是這個方向的正確實作。

## 未量測

- 未能實測 `/api/downloads` 實際回應（Docker daemon 在調查期間死亡，見 `BR_20260809_docker_daemon_and_path_injection_vanish_together.md`）。上述為靜態程式碼推導 + log 佐證。

---

**Closed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n

原始症狀（重啟後下載紀錄全空、UI 永遠看不到歷史檔）已由 `204b2ff` 修復並在 live 驗證：
種入測試檔 → 重啟 → `[Queue] rescan: 1 archived job(s) restored` → API 回 `status='archived'` →
存檔鈕實際取回 200 與精確位元組數。

**本張的「建議修法方案 1」原始寫法（`status='completed'`）永久保留為反面教材**，
不要因為本張已 CLOSED 就以為那段可以照做——它與實際採用的修法差一個字串，後果是 73 個檔案。
