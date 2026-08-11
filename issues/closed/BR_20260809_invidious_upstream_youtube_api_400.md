# BR_20260809: Invidious engine 對 YouTube API 拿到 400/500，首頁是可開的空殼

**Status**: OPEN
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — FIXED — engine 升版後正面量到已修復
**Triage evidence**: 三個逐字列出的失敗端點全部翻轉：trending 200/40670B/565ms、search 200/45803B/3330ms、videos 200/97007B/1392ms，皆帶真實中文標題。控制組（關鍵，因為同 repo 另一張 BR 證明 200 本身零價值）：瞎編路徑 200/0B/466µs ⇒ µs→ms 差三個數量級 + 數萬 bytes 真實內容，證明確實打到上游。修復原因：engine 由 2026.06.15-73a1bac 升至 2026.08.06-d6e4022。

**Filed**: 2026-08-09 by ses_01b53d407ffeRF684F1oTgyEzr（opencode 值星官，服務恢復輪）
**Severity**: 高——服務「看起來上線」但實際無任何內容
**Owner**: 未指派（使用者將於 ytlite repo 自行開 agent）

## 現象

服務已恢復、`https://ytlite.sob.com.tw` 回 200 且 body 是真正的 YT Lite HTML，
但**首頁沒有任何影片**。追到上游是 Invidious engine 打 YouTube 失敗。

## 證據（dispatcher 獨立複驗，非採信 handler 自報）

```
curl http://127.0.0.1:1214/api/videos          -> 200  {"videos":[],"nextPageToken":"2"}
  控制組 /api/zzz-nonexistent                  -> 404   （證明 200 不是路由亂吃）

curl http://127.0.0.1:1215/api/v1/trending?region=TW  -> 500
  body: {"error":"non 200 status code. Youtube API returned status code 400. ..."}
curl http://127.0.0.1:1215/api/v1/search?q=music&type=video -> 400
curl http://127.0.0.1:1215/api/v1/videos/EbMrhOK1BVE        -> 500
```

`docker logs ytlite-engine` 對得上：

```
500 GET /api/v1/trending?region=TW   78.94ms
400 GET /api/v1/search               84.01ms
500 GET /api/v1/videos/EbMrhOK1BVE  375.66ms
```

## 已排除的方向（不要重查）

**companion 是好的，engine↔companion 接線也是好的。**
`docker logs ytlite-companion`：

```
[INFO] Successfully validated PO token with video: EbMrhOK1BVE
[INFO] Successfully generated PO token
--> POST /companion/youtubei/v1/player 200 304ms
```

PO token 拿得到、驗得過、companion 自己回 200。
config.yml:72-75 的 `private_url` + key 與 compose 的 `SERVER_SECRET_KEY` 一致。

所以**故障面在 engine→YouTube 這一段**，不在 engine→companion。

## 值得注意的線索

companion log 反覆出現：

```
[WARNING] No URLs found for adaptive formats. Falling back to other YT clients.
[WARNING] Trying fallback YT client TV_SIMPLY
```

即使在「成功」的路徑上也要 fallback 到 TV_SIMPLY，暗示預設 YT client 已被 YouTube 擋掉。
engine 版本是 `2026.06.15-73a1bac`（HEAD commit 9ff42fa 於 2026-06-19 才升過一次以修 parser）。
**這類問題的常態是 YouTube 端變更 → Invidious 需要跟進版本**，先看 upstream release notes
比在本地 config 裡調參數更省時間。

## 修復前必讀：這個組件的驗證陷阱

見 `BR_20260809_invidious_returns_200_empty_for_unknown_routes.md`。
**`/api/v1/popular` 回 `200 []` 不能當成「這條路通了只是沒熱門片」**，
因為同一個 engine 對**不存在的路徑**也回 `200 []`。驗證修復時務必先建立控制組。

## 範圍說明

本輪任務是「把服務起回來」，此缺陷屬 Invidious/YouTube 上游對抗，
使用者已裁示後續由其自行開 agent 處理，故本輪不修。

**Related**: `BR_20260809_invidious_returns_200_empty_for_unknown_routes.md`
（同一組件；後者是驗證前者時必須先解除的判準陷阱）
