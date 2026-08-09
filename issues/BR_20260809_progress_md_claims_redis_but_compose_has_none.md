# BR: PROGRESS.md 宣稱有 Redis，compose 無 Redis — 文件與現實不一致

- **Filed**: 2026-08-09
- **Filed by**: ses_01b36b5ffffeNy0N6OCtYnJm5n（[★]main ytlite 值星官）
- **Status**: OPEN
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
