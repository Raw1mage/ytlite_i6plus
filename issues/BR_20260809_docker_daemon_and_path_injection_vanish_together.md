# BR: Docker Desktop 停止時 PATH 注入無聲撤除，`command -v docker` 回空與「未安裝」共用同一個輸出

**Filed**: 2026-08-09
**Revised**: 2026-08-09 — 容器全退的成因已由 dispatcher 查明（使用者在 Windows 端操作 Docker Desktop，非主機層故障），本 BR 範圍收斂到真正的缺陷：PATH 注入層 fail-silent-and-misleading
**Status**: OPEN
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — PARTIAL — 主症狀已被結構性移除，殘留未能判定
**Triage evidence**: `command -v docker` → /usr/bin/docker rc=0（控制組 zzz-nosuch → 空 rc=1）。PATH 仍無 docker 注入，但 /usr/bin/docker 現為 symlink → /mnt/wsl/docker-desktop/cli-tools/... ⇒ 不再依賴注入。UNDECIDABLE：symlink 能否撐過 Docker Desktop 停止時的掛載重建，需一次停止事件才能量。

**Severity**: MEDIUM — 不影響 production，但誤導性失敗訊號會讓調查者得出「docker 沒安裝」的反向結論
**Owner**: unassigned
**Related**: `BR_20260809_docker_desktop_registry_proxy_dies_silently_and_recurs.md`（同一個 Docker Desktop / WSL 整合層的不穩定；該張是 registry proxy 死，這張是整個 daemon + PATH 注入死，是更上游的同族故障）

## 症狀（調查途中發生，非事前已知）

同一個 session 內，前段這些指令全部正常：

```bash
docker ps -a                     # rc=0，列出 30 個容器
docker run --rm ytlite-middleware sh -c 'command -v yt-dlp'   # rc=0
docker logs ytlite               # rc=0
```

十幾分鐘後，同樣寫法的指令：

```bash
docker run --rm ... --entrypoint python3 ytlite-middleware /t.py
# → /bin/bash: line 29: docker: command not found     rc=127
```

## 這裡有兩層失效，而它們互相偽裝

### 第一層：PATH 注入消失（誤導性最強的一格）

```bash
command -v docker          # → 空, rc=1
# 負控制組（證明 command -v 真的會對不存在的東西回非 0）：
command -v zzz-nosuch-bin  # → 空, rc=1
# 正控制組（證明它對存在的東西會回 0）：
command -v python3         # → /usr/bin/python3, rc=0
```

到這裡為止，證據看起來就是「docker 沒安裝」。**但那是錯的**：

```bash
test -x /usr/bin/docker                                    # ABSENT
test -x /usr/local/bin/docker                              # ABSENT
test -x /mnt/wsl/docker-desktop/cli-tools/usr/bin/docker   # EXISTS_EXEC  ← binary 一直都在
test -x ~/.docker/bin/docker                               # ABSENT

echo "$PATH" | tr ':' '\n' | grep -i docker                # → 無任何一行
```

**`command -v` 回空有兩種成因——「不存在」與「存在但不在 PATH 上」——而它們共用同一個輸出。** Docker Desktop 的 WSL 整合是把 `/mnt/wsl/docker-desktop/cli-tools/usr/bin` 注入 PATH，那個注入沒了，binary 卻原地未動。

這正是 AGENTS.md「歸責紀律」表列的形狀：**那一格資訊系統當下有沒有？有**（檔案系統知道 binary 在哪，PATH 也知道自己少了什麼），但 `command -v` 不說。

### 第二層：daemon socket 消失

用絕對路徑繞過 PATH 後：

```bash
/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker info
# Server:
# failed to connect to the docker API at unix:///var/run/docker.sock;
# ... dial unix /var/run/docker.sock: connect: no such file or directory   rc=1

test -S /var/run/docker.sock                                             # ABSENT
test -S ~/.docker/desktop/docker.sock                                    # ABSENT
test -S /mnt/wsl/docker-desktop/shared-sockets/guest-services/docker.sock # ABSENT

docker context ls
# default *       unix:///var/run/docker.sock
# desktop-linux   npipe:////./pipe/dockerDesktopLinuxEngine
```

這一層的訊號是**好的**——它明說了 socket 路徑、明說了連不上。與第一層形成對照：同一個故障，一層 fail-loud，一層 fail-silent-and-misleading。

### 觸發情境（成因已查明，非本 BR 的缺陷本體）

```
ytlite           finished=2026-08-09T07:01:25.894199113Z  exit=0  oom=false
ytlite-engine    finished=2026-08-09T07:01:25.4733958Z    exit=0  oom=false
```

30 個容器（含 warroom / bodesign / specbase / patentmcp 等**其他專案**）全部標記為同一時刻退出，`exit=0` 非 OOM。

**成因已定案（dispatcher 查 Windows 端 mtime 取得，2026-08-09）**：

```
/mnt/c/Users/yeats/AppData/Roaming/Docker/settings-store.json  mtime 15:20:15
ContainersProxyHTTPMode = disabled
ProxyHTTPMode          = disabled     ← 使用者關掉的
key 數 22 → 24（控制組：假 key has=false、真 key has=true）
```

序列：15:01 使用者開啟 Docker Desktop（該刻 30 個容器退出）→ 15:20 關閉兩個 proxy → Docker Desktop 未留在背景 → handler 於 07:01Z(=15:01) 觀察到全體退出。

**這是使用者在 Windows 端的正常操作，不是故障。** 本 handler 當時報為「主機層事件」，是在只能看到 WSL 側的前提下所能到達的極限；成因需 Windows 端證據，不在該 session 可視範圍。

**容器退出本身不是缺陷，故不在本 BR 範圍。** 本 BR 保留的是下述那個真缺陷：同一個停止動作**同時**撤掉 PATH 注入與 socket，而前者無聲、後者有聲。

## 影響

調查進行到一半失去全部動態取證能力：無法打 `/api/downloads`、無法進容器看 `DOWNLOADS_DIR` 權限、無法驗證 `app.mount("/downloads")` 與 `@app.get("/downloads")` 的路由優先序。所有這些都被迫降級為靜態推導。

## 處方

**操作面（立即可用）**：本機 docker 的絕對路徑是
`/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker`。
遇到 `docker: command not found` 時，**先 `test -x` 那個絕對路徑再下結論**，不要據 `command -v` 的空輸出判定「docker 沒裝」。

**規則面**：`command -v` 只回答「這個名字在不在 PATH」。凡靠它判定工具存在性的檢查，都應同時附一個 `test -x <已知絕對路徑>` 的第二證據；單獨的空輸出不是缺席的證明。

**根因面**：Docker Desktop 的 WSL 整合會在停止時同時撤掉 PATH 注入與 socket，且撤 PATH 這件事沒有任何告警。若能改用 systemd 管理的原生 docker，或把 CLI 的絕對路徑固定進 PATH（不依賴 Desktop 注入），可讓第一層失效消失，只留下訊號良好的第二層。

## 未量測

- 未量測 PATH 注入是「Docker Desktop 主動撤除」或「shell 環境未重新繼承」——兩者可觀察結果相同，需在停止動作前後各取一次 `/proc/self/environ` 才能分辨。
- 未嘗試重啟 Docker Desktop（派工單明令不得重啟容器，且重啟 Desktop 屬主機層操作，權責在 dispatcher / 使用者）。

## 復發紀錄（第二次，2026-08-09 稍晚）

同一個 session 內第二次發生，形狀逐字一致：

```
command -v docker                                          → 空, rc=1
test -x /mnt/wsl/docker-desktop/cli-tools/usr/bin/docker    → EXISTS_EXEC   ← binary 仍在
  控制組 test -x …/zzz-nosuch                               → absent（證明 test -x 會對真缺席回假）
test -S /var/run/docker.sock                                → ABSENT
<絕對路徑>/docker ps  → "dial unix /var/run/docker.sock: connect: no such file or directory"  rc=1
ss -ltn | grep 1214                                         → 無（控制組：ss 看得到 22/111/631）
```

**本 BR 的處方在這次被實測驗證有效。** 第一反應是 `docker: command not found`，若照字面判定「docker 沒裝」就會得出反向結論；改用本 BR 記載的絕對路徑 `test -x` 後，正確分辨出「binary 在、PATH 注入沒了、daemon 也停了」三件事。

**這也是復發本身的價值**：同一個缺陷形狀在同一天內兩次中斷動態取證，第一次讓 RCA 的三格降級為靜態推導，第二次讓一項 log 時序實測無法完成（見 `BR_20260809_download_jobs_in_memory_only_vanish_on_restart.md` 相關的 undecidable 項）。**成因（使用者操作 Docker Desktop）不是缺陷，但「PATH 注入無聲撤除」讓每一次都要重新付一次診斷成本。**

### 第二次的成因：已查明（dispatcher 於 Windows 端量測，2026-08-09）

原先記為「未量測、不假定與第一次同因」。現已取得證據，**確實與第一次同因**：

```
settings-store.json      mtime 16:16:10        ← 使用者於撞上前 3 分鐘修改
Docker Desktop.exe.log   16:17:34Z  "backend process exited"
tasklist（16:19）           324 行，docker 相關 0 個
                         控制組：explorer.exe=1（有效）、假進程名=0
proxy 欄位              ContainersProxyHTTPMode / ProxyHTTPMode 仍 disabled
```

使用者再次在 Windows 端動 proxy 設定，Docker Desktop 退出且未留在背景（第一次是 15:20 那筆 mtime）。**兩次都是使用者操作，不是主機層意外。**

**下次復發的最快分流（兩格，照跑即可）**：

```bash
stat -c '%y' /mnt/c/Users/yeats/AppData/Roaming/Docker/settings-store.json
tail "/mnt/c/Users/yeats/AppData/Local/Docker/log/host/Docker Desktop.exe.log"
```

mtime 落在事故前幾分鐘 + host log 有 `backend process exited` ⇒ 使用者操作，不是故障。**WSL 側 session 看不到這兩格是結构性的**（無 Windows 端可視範圍），所以實作上這張 BR 的分流須由有 `/mnt/c` 訪存的一方執行。

### 處方的一項修正：絕對路徑也有消失的窗口期

本 BR 先前寫「binary 一直都在」——**不完全準確**。後續實測到三態而非兩態：

```
階段 1（daemon 停、掛載仍在）  command -v docker → 空；test -x <abs> → EXISTS_EXEC
階段 2（掛載拆除/重建窗口期） <abs>/docker → "No such file or directory" rc=127
                                /mnt/wsl/docker-desktop 目錄仍存在，子樹內容未就緒
階段 3（恢復後）              test -x <abs> 與 /usr/bin/docker 雙雙回 EXISTS_EXEC
```

所以「絕對路徑 `test -x`」仍是正確的第二證據，但**它也有回假的時候，而那不代表未安裝**。確認順序應為：`test -x <abs>` → 若失敗再查 `test -d /mnt/wsl/docker-desktop` 與 `grep -c docker-desktop /proc/mounts`（實測恢復後為 72 行）。目錄在而 binary 不在 ⇒ 掛載重建中，等待即可，不是安裝問題。

## 修訂紀錄

- **2026-08-09 初版**：報告容器全退為「主機層事件」，成因不明。
- **2026-08-09 修訂**：dispatcher 以 Windows 端 `settings-store.json` mtime 查明為使用者操作。標題與範圍收斂至 PATH 注入的揭露缺陷；成因段落改列為觸發情境，不再宣稱成因不明。
