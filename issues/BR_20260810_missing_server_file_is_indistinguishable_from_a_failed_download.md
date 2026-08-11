# BR: 伺服器檔案不見了，與下載失敗共用同一個輸出（且那一列永遠清不掉）

- **Status**: OPEN
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — OPEN — 已判定，低（碼仍在，但現況無受害對象）
**Triage evidence**: REPRO（碼）：main.py:1222-1223 `not file_path or not os.path.exists()` 仍合併成同一個 404。前提已消失：/api/downloads 回 200 且 job 陣列長度 0、downloads 目錄 0 檔 ⇒ 目前不存在會卡住的死列。

- **Filed**: 2026-08-10 by ses_01b36b5ffffeNy0N6OCtYnJm5n (dispatcher)
- **Severity**: low（安全，但體驗上是靜默的死列）
- **Owner**: downloads / archived-jobs family
- **Discovered by**: handler ses_01aa0f428ffeMtuttVwLw5ngJR, 在 `archived-not-downloadable` item 1 的 V4'-3（讀碼觀察，未改）
- **Related**: `issues/closed/BR_20260809_disk_rescan_marked_history_completed_and_autosave_deleted_73_files.md`（same family：同一條 archived job 生命週期；那張是「檔還在卻被刪」，這張是「檔沒了卻還在清單上」——互為對偶）

## 現象

一個 `archived` job 的 `file_path` 指向的檔案若被外部刪掉（手動 `rm`、磁碟清理、容器 volume 重建），該列會**永遠留在下載清單上，且無法透過任何 UI 動作消失**：

1. 按「存檔」→ `GET /api/download_file/{id}` 回 404 → 前端 `throw` → catch → fallthrough 到 anchor/iframe → 回 `'unknown'` → **不 purge**（正確，不該假裝成功）
2. 那個 anchor click 指向一個 404 URL → 瀏覽器可能什麼都不做，或存下一個 404 頁面
3. 按「隱藏」（`purge=false`）→ 移出記憶體清單 → **下次 rescan 掃不回來**（檔不在磁碟上）⇒ 這條路徑其實可以清掉它
4. 但使用者不知道要按「隱藏」，因為畫面告訴他的是「下載失敗」

## 根因

`main.py:1219-1220`：

```python
if not file_path or not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File deleted from server")
```

後端**知道**這兩件事是不同的（`not file_path` vs `not os.path.exists`），但把它們合併成同一個 404；而前端把任何非 ok 的回應都轉成同一句：

```
「自動存檔失敗: 伺服器回傳錯誤，將切換至手動模式」
```

⇒ **「檔案在伺服器上已不存在」（永久，重試無用）與「這次下載失敗了」（暫時，重試可能成功）共用同一個可觀察輸出**，而使用者收到的是後者的措辭，於是他會重試，而重試永遠失敗。

這是本 repo 反覆出現的同一個形狀（見 `docs/verification_control_group_three_layer_failure.md`）：兩個不同事實共用一個輸出，且共用的那個是較令人安心的（「失敗了，再試一次」比「這個檔沒了」聽起來可恢復）。

## 為什麼現在不修

- **它是安全的**：不會刪錯檔、不會假報成功。`purge` 守衛正確地擋住了（已在 item 1 的 mutation 驗證中坐實：`unknown` → purged=0）。
- **它不擋主路徑**：使用者裁示只管 PC Chrome 的批次存檔，而那條路徑上檔案是存在的。
- **它是既有行為**，不是 `archived-not-downloadable` 這一包引入的。

## 建議修法（未實作，供未來參考）

**不要**用「rescan 時順手清掉指向不存在檔案的 job」——那會讓 rescan 從純讀取變成會刪狀態的動作，而 rescan 在 `__init__` 裡跑，語意變更的打擊半徑大。

較小的修法是讓後端把這一格的資訊揭露出來，前端據以給不同的措辭與動作：

```
404 detail="File deleted from server"  →  前端顯示「伺服器上已無此檔案」+ 提供「移除此列」
其他失敗                                →  維持「下載失敗，切換手動模式」
```

判準：**這一列的正確動作是「移除」還是「重試」，取決於一格後端已經知道的資訊**（`os.path.exists`）。目前那一格沒有傳到前端，所以使用者拿到的是錯的動作建議。

## 沒量到的

- 沒有實際製造這個狀態來端到端重現（讀碼觀察 + handler 的靜態分析）。目錄裡目前 60 個 mp3 的 `file_path` 全部存在。
- 「隱藏後 rescan 掃不回來」是從 rescan 的實作推得（它只列磁碟上真實存在的 entry），未實跑。
