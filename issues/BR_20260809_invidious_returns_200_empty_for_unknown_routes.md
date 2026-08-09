# BR_20260809: Invidious 對不存在的 API 路徑回 200 空 body，與「有路由但無資料」共用同一個輸出

**Status**: OPEN
**Filed**: 2026-08-09 by ses_01b53d407ffeRF684F1oTgyEzr（opencode 值星官，服務恢復輪）
**Severity**: 中——不影響服務運作，但**會讓修復驗證得出反向結論**
**Owner**: 未指派

## 現象

Invidious engine（`ytlite-engine`, `2026.06.15-73a1bac`）對**根本不存在**的 API
路徑回 `200` 加空 body，與「路由存在但目前沒資料」完全無法分辨。

## 證據（dispatcher 獨立複驗）

```
curl http://127.0.0.1:1215/api/v1/zzz-nonexistent  -> 200
curl http://127.0.0.1:1215/api/v1/popular          -> 200   body: []
```

engine log 自己也印出來了，兩者並排：

```
2026-08-09 04:14:45 [info] 200 GET /api/v1/zzz-nonexistent   92.68µs
2026-08-09 04:15:48 [info] 200 GET /api/v1/popular           98.28µs
```

**兩行看起來一模一樣。** 一個是我瞎編的路徑，一個是真正的 API。

## 為什麼這件事值得建檔

這是典型的**缺席態與失敗態共用同一個輸出**：

| 情境 | 輸出 |
|---|---|
| 路徑不存在 | `200 []` |
| 路徑存在、上游正常、真的沒熱門影片 | `200 []` |
| 路徑存在、上游壞掉、被靜默吞掉 | `200 []` |

三種狀況擠在同一個字串上，判別力為零。

**具體危害**：修 `BR_20260809_invidious_upstream_youtube_api_400.md` 時，很自然
會拿 `/api/v1/popular` 回 200 當成「這條路通了」。它不是證據——它是這個 engine
對**任何**字串的預設回應。照此判準會得出「上游已修好」的反向結論。

## 修復此組件時的正確做法

驗證任何 Invidious endpoint 之前，**先跑控制組建立判別力**：

```bash
# 先證明這個檢查在該失敗時真的會不一樣
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:1215/api/v1/<你瞎編的路徑>
# 若它也回 200，那 200 對你的結論零價值 —— 改看 body 內容或 engine log
```

可用的判別手段：
- 看 **body 實際內容**，不只看 status code
- 看 `docker logs ytlite-engine` 的 **latency**：`92.68µs`（沒打上游）
  vs `375.66ms`（真的打了 YouTube 才失敗）——**這一格是目前最好的判別訊號**
- 用**已知一定有資料**的 endpoint 當正控制組

## 歸責

這不是「驗證者不夠仔細」。那一格資訊 engine 當下**有**（它知道自己沒有這個路由，
才會用 92µs 回覆而非去打上游），但它選擇用 200 回答。屬揭露缺陷，非操作失誤。

**Related**: `BR_20260809_invidious_upstream_youtube_api_400.md`
（同組件；本 BR 是驗證該 BR 時必須先解除的判準陷阱）
