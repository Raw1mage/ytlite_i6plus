# BR: repo 內存在 root-owned 目錄，源於容器以 root 執行並 bind mount 整個 source dir

- **Filed**: 2026-08-09
- **Filed by**: ses_01b36b5ffffeNy0N6OCtYnJm5n（[★]main ytlite 值星官）
- **Status**: OPEN
- **Severity**: low-medium（會在需要清理或 git 操作時卡住，且是持續產生的）
- **Owner**: 未指派
- **Family**: G-deploy-drift

## 現象

`webbox/src/middleware/` 下兩個目錄為 `root:root`，其餘檔案為 `pkcs12:pkcs12`：

- `webbox/src/middleware/__pycache__`
- `webbox/src/middleware/data`

## 根因（已確認，非推測）

`webbox/docker-compose.yml:58` 將 **整個 source 目錄** bind mount 進容器：

```yaml
volumes:
  - ./src/middleware:/app
  - /opt/ytlite_v3/user_db:/app/data
```

而容器內 PID 1 的 uvicorn 以 **root(uid 0)** 執行（`docker exec ytlite ps -ef` 實測）。
因此**容器寫回宿主機的任何東西都會是 root-owned** —— `__pycache__` 是 Python 自動產生的，
`data/` 是第二個 mount 的掛載點。

**這不是一次性汙染，是持續機制**：只要容器以 root 跑且 bind mount source dir，就會不斷產生。

## 為什麼「刪掉就好」不是修法

`sudo rm -rf __pycache__` 會讓它下一次啟動時再長回來。真正的修法有三條路，成本遞增：

1. 容器內加 `PYTHONDONTWRITEBYTECODE=1`（只治 `__pycache__`，不治其他寫回）
2. 容器改以非 root user 執行（`user: "1000:1000"`），但需確認 `/app/data` 的 root-owned 檔案仍可讀寫 —— **會與現有 `/opt/ytlite_v3/user_db` 的 root:root 644 衝突**
3. 不 bind mount 整個 source dir，改為 build 進 image（但目前 build 路徑壞掉，見 Related）

## 未量測

- 未確認除了這兩個目錄外，是否還有其他被容器寫回的 root-owned 檔案
- 未實測方案 2 是否會導致 `/app/data` 讀寫失敗（**這一格是關鍵**：若改 user 後讀不到 client_secret.json，OAuth 會整條壞掉）
- 未確認 `.gitignore` 是否已涵蓋 `__pycache__`（若未涵蓋，root-owned 檔案還會干擾 git 操作）

## Related

- `BR_20260809_docker_build_path_broken_cannot_rebuild_image.md`（修法 3 需要能 rebuild image，而 build 路徑目前壞掉 —— 前置依賴）
- `BR_20260809_secrets_hardcoded_in_compose_and_config_no_env_file.md`（同族：都是 compose 層的部署設計問題，且都需要動 compose 才能修）
