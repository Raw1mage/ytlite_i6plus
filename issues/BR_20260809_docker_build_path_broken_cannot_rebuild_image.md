# BR_20260809: docker build 路徑整條壞掉，ytlite image 無法 rebuild

**Status**: OPEN
**Filed**: 2026-08-09 by ses_01b53d407ffeRF684F1oTgyEzr（opencode 值星官，服務恢復輪）
**Severity**: 中——不影響「服務跑起來」，但**鎖死在 3 個月前的依賴上**
**Owner**: 未指派
**⚠ 根因在 host docker 環境，不在 ytlite repo**——此 BR 放這裡是因為它直接擋住 ytlite
的 rebuild，不是主張 ytlite 該負責修。

## 現象

兩條 build 路徑都死，且**死在完全不同的地方**。服務本身完全正常
（`docker ps` / `docker run` / 既有 image 全部可用），只有 **build** 不能跑。

## 證據（dispatcher 獨立複驗）

**路徑一：buildx**（`webctl.sh up --rebuild` 走的）

```
request returned 500 Internal Server Error for API route and version
http://%2Fvar%2Frun%2Fdocker.sock/v1.54/version,
check if the server supports the requested API version: driver not connecting
```

錯誤訊息把它講成**版本協商問題**，實際不是：

```
curl --unix-socket /var/run/docker.sock http://localhost/version  -> 000（8s timeout，0 bytes）
控制組  同 socket /_ping                                          -> 200
```

`/_ping` 好的、`docker ps` 好的、`docker info` 拿得到 server 29.6.2 —— **只有
`/version` 這一個 endpoint 掛住**。buildx 靠它協商，所以只有 build 死。

**路徑二：legacy builder**（`DOCKER_BUILDKIT=0`）

```
failed to resolve reference "docker.io/library/python:3.10-slim":
proxyconnect tcp: dial tcp 172.29.0.1:3128: connect: connection refused

控制組  直接測 172.29.0.1:3128  -> REFUSED
```

## proxy 從哪來：UNVERIFIED

已排除的位置（都查過，都沒有）：

```
/etc/systemd/system/docker.service.d/*.conf   無 proxy drop-in
/etc/docker/daemon.json                        只有 auths，無 proxy
~/.docker/config.json                          無 proxies 區段
我的 shell env                                 無 *_proxy
```

**`pgrep -x dockerd` 回空**，但 docker socket 正常回應 —— 這台是 WSL + Docker
Desktop 整合，dockerd 跑在另一個 distro。所以 proxy 極可能設在 **Docker Desktop
的 Windows 側設定**，本 WSL 內查不到，也修不到。

沒有繼續往下查，因為那已離開 ytlite 範圍。

## 目前的迴避方式（**繞過去，不是修好**）

本輪不 rebuild，直接用既存 image + bind-mount 原始碼啟動：

- compose 把 `./src/middleware` bind-mount 進 `/app` → **Python 原始碼是新的**
- 但 image 內的 **pip 依賴是 3 個月前的**

若 `requirements.txt` 這 3 個月有變動，缺的套件不會被裝上。
目前跑起來沒噴 ImportError，**那是間接證據，不是證明**。

## 影響

- 任何需要改 `requirements.txt` 的工作（升 yt-dlp、加套件）**現在做不到**
- yt-dlp 釘在 `2026.3.17`，這類套件通常需要跟著 YouTube 變更頻繁更新 ——
  與 `BR_20260809_invidious_upstream_youtube_api_400.md` 可能有關聯

## 歸責

`/version` 掛住卻回報成「版本不支援」，是**缺席態與失敗態共用輸出**的變體：
真正的事實（那個 endpoint 沒有回應）系統當下知道（`/_ping` 200 證明 socket 活著），
但錯誤訊息引導讀者去查自己的 client 版本。屬揭露缺陷。

**Related**: `BR_20260809_invidious_upstream_youtube_api_400.md`
（若該問題的修法需要升 yt-dlp / 改依賴，會先撞到本 BR）
