# BR: include_granted_scopes=true 讓同專案其他 app 的 scope 被拖進授權請求

- **Filed**: 2026-08-09
- **Filed by**: ses_01b36b5ffffeNy0N6OCtYnJm5n（[★]main ytlite 值星官）
- **Status**: OPEN — 現況不發作，但機制未移除
- **Severity**: medium（潛伏型：會在「專案裡多了一個 app」這個看似無關的動作後突然發作）
- **Owner**: 未指派
- **Family**: G-oauth

## 現象（已實際發生過一次）

2026-08-09，OAuth client 建在 Thesmart 專案（與「利善美智能」同專案）時，
使用者點下 `/login` 收到：

```
This request contains scopes that cannot be requested together:
[youtube.force-ssl, youtube.readonly, drive.file]
錯誤 400: invalid_request
```

**`drive.file` 不在 ytlite 的程式碼裡**（`main.py:44` 的 `SCOPES` 只有兩個 youtube scope；
全檔 `grep 'drive'` 命中 0，控制組 `grep -c 'def '` = 47 證明 grep 讀得到該檔）。

## 根因

`webbox/src/middleware/main.py:267` 的 `include_granted_scopes='true'`。
該參數要求 Google 把**使用者先前在同一專案下已授權的 scope 一併合併**進本次請求。
「利善美智能」在 Thesmart 下取得過 `drive.file`，於是被合併進來，撞上 Google
「youtube.* 與 drive.file 不可同時請求」的互斥限制。

## 現況為何不發作 —— 這一格是本 BR 的重點

已將 client 遷至 Project-Raw（client_id 前綴 `134400565981`）。該專案目前只啟用
`iap.googleapis.com` + `youtube.googleapis.com`，**沒有第二個會索取其他 scope 的 app**。

**所以現在能通，是因為「碰巧沒東西可合併」，不是因為機制被修好。**
`include_granted_scopes='true'` 原封不動。日後只要 Project-Raw 加入任何索取其他
scope 的 app，同一個故障會原樣重演——而屆時的觸發動作（「在 GCP 加一個 app」）
看起來與 ytlite 毫無關係，會非常難聯想。

## 建議修法

**刪掉 `main.py:267` 的 `include_granted_scopes='true'`**（或改 `'false'`）。

ytlite 只需要自己宣告的兩個 youtube scope，從未需要增量授權。這個參數對本專案
沒有任何用處，只帶來耦合。

代價：需重啟 `ytlite` 單一容器（uvicorn 無 `--reload`；只重啟這一個，不影響
engine/companion/postgres，也不碰 Docker Desktop 與其他 17 個容器）。

同檔另有 `legacy_code_archive/app.py` 也含此字串（repo grep 命中 2 檔），
修改前需確認該檔是否為 live 路徑。

## 未量測（明列，不得當成已排除）

- **`include_granted_scopes` 的合併邊界是 per-project 還是 per-account，未經實證。**
  本 BR 假設是 per-project（因遷專案後不再發作），但那是**單一觀察**，不是控制實驗。
  若實為 per-account，遷專案根本不是有效緩解，只是這次剛好沒撞到。
- 未實測刪除該參數後 OAuth 流程是否完全正常（需改 code + 重啟才能驗）
- `legacy_code_archive/app.py` 是否為死碼未確認

## 為什麼這格量不到

`accounts.google.com/o/oauth2/auth` **對所有請求都先回 302**，包含故意用假 client_id 的請求
（值星官實測：假 client_id 也回 302）。錯誤只在使用者實際載入下一頁時才出現。
所以 curl 探測在這件事上**零判別力**——「正常」與「壞掉」共用同一個輸出。
要驗證只能靠真人點同意畫面。

## Related

- `BR_20260809_secrets_hardcoded_in_compose_and_config_no_env_file.md`
  （同族：都是「設定的隱含耦合散落在單一行、沒有任何機制在使用點提示風險」）
- 本 BR 與 `BR_20260809_invidious_returns_200_empty_for_unknown_routes.md` 共享同一個缺陷形狀：
  **缺席態與失敗態共用同一個輸出**。前者是 Invidious 對未知路徑回 200 空 body，
  後者是 Google OAuth 端點對合法與非法請求都回 302。
