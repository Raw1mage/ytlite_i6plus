# BR_20260809: Docker Desktop 內建 registry proxy 反覆死亡，無人配置、無人監控、失敗訊息不指向真因

**Status**: OPEN（已有繞路工具，未根治）
**Filed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（ytlite 值星官）
**Severity**: 中——不影響已運行容器，但**完全阻斷映像升級**，且症狀會被誤讀為網路問題
**Owner**: 未指派（根治需使用者在 Docker Desktop UI 操作）

## 現象

`docker compose pull` / `docker pull` 全部失敗，錯誤訊息指向 registry 連線：

```
failed to resolve reference "quay.io/invidious/invidious:2026.08.06-d6e4022":
  failed to do request: ... proxyconnect tcp: dial tcp 172.29.0.1:3128: connect: connection refused
```

## 證據（dispatcher 獨立量測）

| 檢查 | 結果 |
|---|---|
| `/etc/docker/daemon.json` | **無 proxy 字樣** |
| `~/.docker/config.json` | **無 proxy 字樣** |
| `docker info` | `HTTP Proxy: http.docker.internal:3128` |
| process 表 | `/run/docker-desktop/docker-desktop-user-distro proxy --distro-name Ubuntu-24.04` |
| Windows 端 `settings-store.json` | proxy 五個欄位**全部 `has=false`**（控制組：假 key 也回 false） |
| 宿主機直連 quay.io | **`401`** = registry 要 token 的正常握手（控制組：假 host 回 `000 rc=6`） |
| `3128` 埠 | **REFUSED**（控制組：同時測 `1214` 為 OPEN，證明探測法有效） |

**兩件事同時成立**：機器本來就直連得到 registry；那支被強制插進來的 proxy 死了。

## 為什麼值得建檔

**這是舊病復發，不是新問題。** `~/.cache/ytlite-imgpull/ocipull.py` 的第一行 docstring
寫著 *"bypassing dockerd's dead proxy"* —— 某輪的我或使用者**已經為它寫過繞路工具**，
代表它至少死過兩次，而中間沒有任何人知道它又活了或又死了。

三格構成這個缺陷的完整形狀：

1. **沒有人配置它** —— 兩端設定檔都沒有 proxy 欄位，是 Docker Desktop 在 WSL2 下的
   內建預設管線。使用者原話：「這不是我的旨意建立的」。
2. **沒有人監控它** —— 它死掉不影響已運行容器，所以可以死很久而沒有任何訊號，
   直到某次要拉映像才發作。
3. **失敗訊息不指向真因** —— `connection refused` 讀起來像網路問題或 registry 掛了，
   而真相是「本機一個沒人要的中間層死了，繞過它就好」。

**具體代價（本輪實錄）**：dispatcher 因為容器間網路測通，就宣告「Docker proxy 沒死」，
把假設推翻方向搞反，多花一輪才定位。**「容器網路通」與「registry proxy 活著」是兩件事**，
共用「docker 看起來正常」這個外觀。

## 目前的繞路（可用，非根治）

`python3 ~/.cache/ytlite-imgpull/ocipull.py <image:tag>` —— 直連 registry 拉 OCI layer，
verify digest + verify size，mismatch 即 `sys.exit`（不是「下載完就當成功」的寫法）。
本輪用它成功拉了 engine 與 companion 兩個映像。

## 根治選項與各自的問題

| 選項 | 問題 |
|---|---|
| 寫 `/etc/docker/daemon.json` | **無效且安靜地無效**——`dockerd` 不在此 WSL 內跑（控制組：同一個 ps 寫法抓得到 `docker-desktop-user-distro`），該檔沒人讀，寫了不報錯 |
| 寫 Windows 端 `settings-store.json` | 未經驗證：無證據證明加哪個欄位能關掉內建 proxy，且 Docker Desktop 可能開機覆寫 |
| **Docker Desktop UI → Resources → Proxies** | **唯一有狀態回饋的路徑**，但只有使用者點得到 |

## 歸責

不是「操作者不夠仔細」。那一格資訊系統當下**有**（`docker info` 一直在印那個 proxy），
但它從不主動揭露「這個 proxy 是我自己插的、你沒有要求、而且它現在死了」。屬揭露缺陷。

## 追記 2026-08-09 15:40 — UI 關閉 proxy 無效，設定與行為脫鉤（**本 BR 最重要的一格**）

使用者於 15:20 在 Docker Desktop UI 關閉 proxy，設定確實寫進檔案：

```
/mnt/c/Users/yeats/AppData/Roaming/Docker/settings-store.json   mtime 15:20:15
ContainersProxyHTTPMode = disabled
ProxyHTTPMode           = disabled
key 數 22 → 24    （控制組：假 key has=false、真 key AutoDownloadUpdates has=true）
```

**但 daemon 完全不甩它。** Docker Desktop 隨後被冷啟動（app 原本整個不在
進程表中，tasklist 311 行、`explorer.exe`=1 證明探測有效、Docker 相關 0 個），
**所以它讀的就是改過的設定檔，不存在「未套用」的可能**：

```
docker info   → HTTP Proxy: http.docker.internal:3128     ← 沒變
              → HTTPS Proxy: http.docker.internal:3128
              → No Proxy: hubproxy.docker.internal:5555
   控制組：假字串 0 命中／正控制組 'Server Version' 1 命中

docker pull hello-world:latest
              → proxyconnect tcp: dial tcp 172.29.0.1:3128: connect: connection refused
   （與關閉前逐字相同）
```

### 這使缺陷升級

原本的形狀是「一支沒人配置、沒人監控的 proxy 死了」。現在多一層：

**使用者透過官方 UI 明確關閉它，設定被接受、被寫入、被讀取，而行為毫無改變。**

三種狀況對使用者共用同一個外觀：

| 情境 | UI 顯示 | 實際行為 |
|---|---|---|
| proxy 已關閉且生效 | 關閉 | 直連 |
| **proxy 已關閉但那兩個欄位管不到它** | **關閉** | **仍走 proxy** |
| 設定沒寫進去 | 關閉 | 仍走 proxy |

**中間那格是本案。** 使用者做了正確的操作、得到正確的回饋、而問題原封不動——
這比「操作失敗並報錯」更糟，因為它會讓人以為這條路已經試過了。

### 尚未確定的（明講，不猜）

`ProxyHTTPMode` / `ContainersProxyHTTPMode` 究竟控制什麼，以及
`http.docker.internal:3128` 由哪個機制注入，**本輪未查證**。
`No Proxy: hubproxy.docker.internal:5555` 這行暗示它與 Docker Desktop
內建的 hub proxy 有關，但這是**推測不是量測**。

`/mnt/c/ProgramData/DockerDesktop/admin-settings.json` 不存在（控制組：
同目錄假檔名也回 absent），故不是企業 policy 覆寫。

### 現況處置

**繼續用 `ocipull.py` 繞路。** 它已多次證明可用（今日拉了 engine 與
companion 兩個映像，digest + size 皆驗證，mismatch 即 `sys.exit`）。
在查清注入機制之前，不建議再對 Docker Desktop 設定做未經驗證的嘗試。

**Related**: `BR_20260809_image_version_drift_latest_tag_hides_staleness.md`
（同族：兩者都讓「映像該升級」這件事在該發聲時保持沉默——一個是版本標籤不揭露版齡，
一個是升級通道死掉不揭露自己存在）
