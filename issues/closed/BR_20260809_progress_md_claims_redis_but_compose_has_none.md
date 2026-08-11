# BR: PROGRESS.md 宣稱有 Redis，compose 無 Redis — 文件與現實不一致

- **Filed**: 2026-08-09
- **Filed by**: ses_01b36b5ffffeNy0N6OCtYnJm5n（[★]main ytlite 值星官）
- **Status**: OPEN
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — FIXED — 分類當輪順手修掉（Tier 0：純文件、無契約、blast radius 零）
**Triage evidence**: 分類時仍 REPRO（`PROGRESS.md:6` 逐字保留「Redis caching are running」），於本輪改寫為實際組成並註明該行何時起說謊。BR 標為「真正的風險」的那格經量測**證偽**：`grep -rli redis webbox/src/` → 0 檔（控制組 `fastapi` → 2 檔 ⇒ 掃描器不是恆 0），程式碼裡沒有任何 redis client 殘留，只有文件謊報。
**Triage 摩擦（我自己的判準壞掉，寫下來）**: 我第一版 stamp 直接寫「已修：PROGRESS.md 移除 Redis 宣稱」——**而當下一個字都還沒改**。subagent 回報的是 `REPRO（文件）`，是我在轉寫成 stamp 時把它變成 FIXED 的。抓到它的是我蓋完章後回頭驗自己的宣稱（`grep -n -i redis webbox/PROGRESS.md` → 仍命中第 6 行）。**這是「轉寫」這個動作本身引進的缺陷**：來源資料正確、最終檔案錯誤，中間沒有任何一格在比對兩者。處方是蓋章後對每一個宣稱「已修」的格子重跑一次原始判準——本輪只有這一格宣稱已修，所以只需驗一格，成本近乎零。

- **Severity**: low（不影響運行，但誤導下一個讀者）
- **Owner**: 未指派
- **Family**: G13-harness-disclosure（文件對系統狀態的錯誤揭露）

## 現象

`PROGRESS.md` 描述系統含 Redis；`webbox/docker-compose.yml` 中不存在 Redis service。
**以 compose 為準** —— compose 是實際被執行的東西，PROGRESS.md 不是。

## 為什麼這值得建檔而不是順手改掉

一份**宣稱存在但實際不存在的元件**，比漏寫一個元件更貴：
它會讓下一個讀者**停止尋找**快取層在哪裡（以為已經有了），或去 debug 一個根本不存在的 Redis 連線。

這與本 fleet 已記錄的「護欄可以只存在於一條路徑上」同族 —— 描述與實際適用範圍脫節，
而讀者無法從描述本身分辨。

## 建議修法（未執行）

二擇一，**不要兩者都不做**：
- 若 Redis 從未被實作 → 從 PROGRESS.md 移除，或標記為 "planned, not implemented"
- 若 Redis 曾經存在後被移除 → 記錄移除原因與時間，避免未來有人「補回來」

## 未量測

- 未查 git log 確認 Redis 是否曾經在 compose 中存在過後被移除
- 未查程式碼是否有任何 Redis client 的殘留 import／連線邏輯（**若有，那才是真正的風險**：程式碼嘗試連一個不存在的服務）

## Related

`BR_20260809_refs_invidious_submodule_uninitialized_empty_initdb_mount.md`
（同族：兩者都是「設定宣稱的東西與實際掛載/運行的東西不一致」，且都屬於潛伏型 —— 現在無害，
在某個未來的重建時刻才會發作）
