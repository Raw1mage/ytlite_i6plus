# BR: image 版本漂移 — compose 指定與本機實存不一致，三個 invidious 版本並存

- **Filed**: 2026-08-09
- **Filed by**: ses_01b36b5ffffeNy0N6OCtYnJm5n（[★]main ytlite 值星官）
- **Status**: OPEN
- **Severity**: low-medium（現況可運作，但重建時行為不可預測）
- **Owner**: 未指派
- **Family**: G-deploy-drift

## 現象

1. `webbox/docker-compose.yml:5` 指定 `postgres:14`，但本機另存在 `postgres:17-alpine`
2. 本機同時存在 **3 個 invidious image 版本**
3. companion 使用 `latest` tag — `latest` 不是版本，是一個會漂移的指標

## 為什麼這是問題而不只是雜亂

**`latest` 讓「現在跑的是什麼」變成不可查的事實。** 本輪實測：companion 跑的 `latest` 解析到
7 週前拉的 `sha256:4dbe5c51`，而 quay.io 上的 `latest` 早已指向 `2026.08.07-02f9443`。
兩者共用同一個 tag 名稱 —— **「已是最新」與「7 週前的舊版」在 `docker ps` 的輸出上完全一致**。

這與本 repo 已建檔的其他缺陷同族：缺席態與失敗態共用同一個輸出。

## 建議修法（未執行，待裁示）

- 所有 image 改用明確版本 tag（含 digest 更佳：`image@sha256:...`）
- postgres 版本對齊：確認實際跑的是 14 還是 17，compose 與現實二擇一對齊
- 清理不再使用的 invidious image（**注意**：清理前需確認哪個是 running 容器所用，否則會誤刪）

## 未量測

- **未確認 postgres 容器實際跑的是哪個版本**（compose 寫 14，但未 `docker exec` 查 `SELECT version()`）
- 未確認 3 個 invidious image 各自被誰引用、可否安全刪除
- 未評估 postgres 14→17 若要升級的資料遷移成本

## Related

`BR_20260809_docker_build_path_broken_cannot_rebuild_image.md`（build 路徑壞 + registry proxy 死，
導致目前**無法**拉新 image 也無法 rebuild —— 本 BR 的修法在那條修好之前無法執行。兩者為前置依賴關係）
