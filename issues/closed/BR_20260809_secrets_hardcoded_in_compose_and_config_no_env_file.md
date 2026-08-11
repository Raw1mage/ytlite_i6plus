# BR: compose 與 config 中硬編碼 secret，且無 .env 隔離

- **Filed**: 2026-08-09
- **Filed by**: ses_01b36b5ffffeNy0N6OCtYnJm5n（[★]main ytlite 值星官）
- **Status**: CLOSED — 2026-08-11 使用者裁示只輪替現行 Postgres 密碼、不重寫歷史；新密碼只存於 ignored `webbox/.env`，舊公開值已失效
**Closed**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main)
**Triage**: CLOSED — SERVER_SECRET_KEY 與 POSTGRES_PASSWORD 均已抽至 ignored `webbox/.env`；tracked 檔只保留 fail-fast 環境變數引用與 `.env.example` placeholder。
**Closure evidence**: `git check-ignore -v webbox/.env` 命中且 `git ls-files webbox/.env` 缺席；`docker compose config --quiet` 通過；tracked 檔中舊 Postgres 字面值 0 命中。資料庫角色已輪替：compose 網路上的獨立 Postgres client 使用新密碼查詢成功、舊公開密碼被拒絕。重建 `invidious-db` / `invidious` 後 DB healthy、engine API 與 middleware HTTP 皆正常，近五分鐘無 auth/FATAL/Exception。使用者裁示：不重寫 Git 歷史，舊值因輪替失效而接受歷史殘留。

- **Severity**: medium（自架單機服務，非公開多租戶；但 secret 進 git 是不可逆的）
- **Owner**: 未指派
- **Family**: G-secret-hygiene

## 現象

三處硬編碼且已進版控：

1. `webbox/docker-compose.yml:14` — postgres 密碼字面值 `password`
2. `webbox/docker-compose.yml:30` + `BUILD/invidious/config.yml:75` — `SERVER_SECRET_KEY` 硬編碼於**兩個檔案**
3. 專案無 `.env`，亦無 `.env.example`；secret 直接寫在會被 commit 的檔案內

## 為什麼第 2 項比它看起來危險

`SERVER_SECRET_KEY` 出現在兩處且**必須保持一致**：engine 與 companion 用它互相認證。
改一邊不改另一邊 → 兩者之間的信任鏈斷裂，但**症狀不會指向 secret**（會表現成 API 呼叫失敗）。
這是典型的「隱含契約散落在兩個檔案、沒有任何機制保證同步」。

## 建議修法（未執行，待裁示）

- 抽到 `.env`，compose 用 `${VAR}` 引用；提供 `.env.example` 進版控、`.env` 進 `.gitignore`
- `SERVER_SECRET_KEY` 若必須兩處出現，加一個 check 腳本斷言兩處相等；或讓 config.yml 由 entrypoint 從 env 生成
- **注意**：已進 git 歷史的 secret，加 `.gitignore` 不會使其消失。需評估是否值得 rewrite history（本 repo 未推 remote 時成本低）

## 未量測

- 未確認 repo 是否曾推上任何 remote（若曾推出，secret 外洩範圍需重新評估）
- 未實測改 `SERVER_SECRET_KEY` 單邊是否真的會斷（推論自架構，未做破壞性驗證）

## Related

`BR_20260809_docker_build_path_broken_cannot_rebuild_image.md`（同一批本輪清查出的部署衛生問題；且 build 路徑壞掉意味著即使改了 config.yml 也無法 rebuild image 使其生效——兩者在「修復可行性」上耦合）
