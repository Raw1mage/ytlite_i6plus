# BR: auto-save 靠「排除清單」而非「白名單」決定該刪哪些檔，護欄一行之遙

**Filed**: 2026-08-09
**Status**: OPEN-DEFERRED（使用者裁示 2026-08-09 停止本功能的後續開發，方向 3 不做）— 防禦深度債。事故已由狀態分離（`204b2ff`）阻斷，本 BR 是那道護欄底下的結構脆弱性
**Severity**: MEDIUM — 目前無害，但它是 2026-08-09 刪檔事故能夠發生的**結構條件**，且復發只需改動一行
**Owner**: unassigned

## 使用者裁示（2026-08-09，收線）

使用者實測後回報：「我看到檔案出現在我的本地資料夾了。所以我猜這個界面它判斷我已經下載好了，才會瞬間清除而不通知。既然這樣，這個功能沒有再處理的必要了。」

**他的診斷正確，而且推翻了整個工作包的前提**：他原本報的症狀（「一秒跳完成並清掉、沒機會按下載」）不是缺陷，是 `autoSaveJob` 在 `downloadDirHandle` 已授權下拿到 `'confirmed'`（真的驗到本機副本落地）後 `purge=true` 釋放伺服器副本——**全流程成功**。截圖的綠勾 toast「已存檔: …mp3」與「已選: Downloads」即為證。

故本 BR 的方向 3（白名單式判準）**不會被實作**。保留本檔而非歸檔，理由：

1. 結構脆弱性**仍然存在**——安全性質仍靠「七個 filter 都不含 `archived`」這個「什麼都沒發生」的性質維持。裁示停止的是開發，不是讓風險消失。
2. 若未來有人在那七行任一處加上 `archived`，事故條件立即恢復。本檔是那時唯一的線索。

**不得**把本檔讀成「已評估為無風險」。它是「已被判定為不修」，兩者不同。
**Related**:
- `BR_20260809_disk_rescan_marked_history_completed_and_autosave_deleted_73_files.md`
  （**因果直系，同一 kill chain**：本 BR 是該事故「根本修法」三個方向裡的**方向 3**，事故當下未做。
  方向 1（狀態分離 `archived`）已於 `204b2ff` 落地並驗證，該 BR 自身已 FIXED；
  但它的閉環條件是 **1 + 3**，方向 3 就是本 BR，故拆出獨立追蹤而非隨事故 BR 一起歸檔）
- `BR_20260809_download_jobs_in_memory_only_vanish_on_restart.md`
  （**同一組件**：`rescan_download_dir()` 是本 BR 所述消費者的資料來源；該 BR 已 FIXED）

---

## 一句話

`readyJobs` 這類 auto-save 消費者用的是**排除式判準**（「status 是 `completed` 或 `finished` 就拿去存、存完刪伺服器檔」），
而不是**白名單式判準**（「這個 job 是我這個 session 叫它下載的，所以存完可以刪」）。
於是任何**新出現的、語意上不該被自動刪除的 job**，只要它的 status 落進那個集合，就會被自動刪掉——
而它是否落進去，取決於別人在別的檔案裡寫了哪個字串。

## 為什麼這是結構問題而不是已修好的問題

事故已經阻斷了，但**阻斷的方式是「讓歷史檔的 status 不在那個集合裡」**。也就是說：

```
現在的安全性質  =  七個 filter 都不含 'archived'
              ↑ 這是一個「什麼都沒發生」的性質，靠七處各自不寫某個字串維持
```

七個 status filter（`204b2ff` 驗證時逐一枚舉）：

| 位置 | 消費者 | 終點 |
|---|---|---|
| `base.html:2745` | `readyJobs` → `autoSaveJob` | `DELETE purge=true` |
| `base.html:2770` | `activeDl` | 計數器（無副作用） |
| `base.html:2960` | `downloadAllFiles` | `DELETE purge=true` |
| `base.html:2983` | `clearFinishedDownloads` | `DELETE purge=false` |
| `downloads.html:237` | `readyJobs` → `autoSaveJob` | `DELETE purge=true` |
| `downloads.html:397` | `downloadAll` | `DELETE purge=true` |
| `downloads.html:422` | `clearFinished` | `DELETE purge=false` |

**七個裡有四個的終點是 `purge=true`。** 任何人在其中任一個加上一個 status 值，就是在改一個安全性質——
而那行 code 看起來只是一個 filter。

**這正是事故的形狀**：`b29dd09` 沒有動任何 filter，它只是在**另一個檔案**裡把一批 job 的 status 寫成了
`'completed'`。加害者與受害者相距七個 filter 之遠，而型別系統、測試、review 全都看不到那條連線。

## 修法方向

把判準從「這個 status 不該被自動處理」翻轉成「這個 job 是本 session 發起的，所以可以」：

```
現在  jobs.filter(j => j.status === 'completed' || j.status === 'finished')
      ← 排除式：所有未來的新狀態預設「會被自動刪」，除非有人記得排除它

改成  jobs.filter(j => sessionInitiated.has(j.job_id) && (j.status === 'completed' || ...))
      ← 白名單式：所有未來的新狀態預設「不會被自動刪」，除非有人明確加入
```

`sessionInitiated` 由前端在成功呼叫 `POST /api/download` 後記錄 job_id（記憶體即可，不需持久化——
重啟後本來就沒有「本 session 發起的下載」）。

**這個翻轉的價值不在於它修掉某個現存 bug**（現在沒有），
而在於它讓**預設值變成安全的**：下一個 rescan、下一個匯入功能、下一個 status 值，都不必依賴作者記得七個 filter 的存在。

## 為什麼不現在就做

1. 需要動四個 `purge=true` 消費者的判斷邏輯，打擊半徑比狀態分離大得多
2. `sessionInitiated` 的生命週期需要設計（分頁重整算不算同一 session？兩個分頁同時開？）
3. 事故已阻斷，這是防禦深度不是止血

## 驗證這一格時要注意

**「七個 filter 不含 archived」這種性質的測試會恆真**——它斷言的是「某個字串不存在」，
而一個壞掉的檢查（抽不到 filter、regex 打不中）也會回報「不存在」。
`204b2ff` 的驗證用的手法是：**先斷言抽到了 7 個 filter**，再斷言每一個都排除 archived，
並且對每一個各做一次 mutation（加上 archived）確認它會被放行。
若要為本 BR 的修法寫測試，同樣需要覆蓋率斷言 + mutation，否則「白名單生效」與「測試沒跑到」共用同一個綠燈。
