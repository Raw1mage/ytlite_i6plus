# BR_20260809: refs/invidious submodule 未初始化，postgres initdb 掛載點是空目錄（潛伏型）

**Status**: OPEN（潛伏——目前完全無害，且**完全看不出來**）
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — OPEN — 已判定，⚠ 原 RCA 錯誤，建議修法無效（見下）
**Triage evidence**: claim 證偽：`git submodule status` → 749791cd… 無 `-` 前綴 ⇒ 已初始化，refs/invidious/config/sql/ 有 9 個 .sql。真因是**路徑錯位**：compose:10 的 ./refs/… 相對於 webbox/，實測掛的是 webbox/refs/invidious/config/sql（root:root、0 entries），而 submodule 在 repo root 的 refs/。⇒ `git submodule update --init` 這個建議修法無效，要改的是 compose 路徑。（該空目錄本身是 root-owned-dirs 那張 BR 的機制產物 —— postgres 容器啟動時自動建出缺失掛載點。）

**Filed**: 2026-08-09 by ses_01b53d407ffeRF684F1oTgyEzr（opencode 值星官，服務恢復輪）
**Severity**: 低（現在）／高（一旦觸發）
**Owner**: 未指派

## 現象

`webbox/docker-compose.yml:10` 把 `./refs/invidious/config/sql` 掛成 postgres 的
`/docker-entrypoint-initdb.d`，但該目錄是**空的**——`refs/invidious` submodule
從未 init。

## 為什麼現在沒事

`/opt/ytlite_v3/postgres_data` 已經初始化過，postgres 的 initdb 只在資料目錄為空時
執行。所以這輪啟動時：

- initdb 腳本**沒有跑**
- postgres 回報 `Up (healthy)`
- 一切正常

## 危害（觸發條件與後果）

一旦 `/opt/ytlite_v3/postgres_data` 被清掉或換到新機器：

```
initdb 執行 -> 掛載點是空的 -> 沒有任何 schema 被建立
            -> postgres 仍然啟動成功
            -> 仍然回報 healthy
            -> Invidious 對著一個沒有 table 的 DB 跑
```

**「schema 建好了」與「什麼都沒建」共用同一個輸出**：兩者都是 `Up (healthy)`。
這是缺席態與失敗態共用輸出的教科書案例，而且它會在**重建環境**時才發作——
正是最沒有餘裕除錯的時刻。

## 建議修法

```bash
cd ~/projects/ytlite && git submodule update --init --recursive
# 然後確認掛載點真的非空（控制組：確認這個檢查在空目錄時會回 0）
ls webbox/refs/invidious/config/sql/ | wc -l
```

若 submodule 來源已不可用，則應把 compose 的該行掛載**移除**而非留一個空目錄——
留著等於在系統裡放一個不會響的警報。

## 本輪為何沒修

不在「把服務起回來」的範圍，且動它會多一個變因。**已確認不影響當前運行**。

**Related**: 無同族先例 — 本 repo 首件 submodule/掛載類缺陷
