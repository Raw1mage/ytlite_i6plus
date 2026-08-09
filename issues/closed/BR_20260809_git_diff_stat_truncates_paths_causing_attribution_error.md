# BR_20260809: `git diff --stat` 截斷路徑，導致改動歸屬誤判（把別人的改動讀成自己的）

**Status**: OPEN
**Filed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（ytlite 值星官）
**Reported-by**: ses_01aeeafd6ffeO3Js1AojHkn9zz（handler，主動揭露；即使它自己已繞過）
**Severity**: 中——在**多方共用同一棵工作樹**時會導致錯誤的 commit 範圍
**Owner**: 未指派

## 現象

handler 跑 `git diff --stat` 檢查自己改了什麼，輸出中出現 `webbox/docker-compose.yml`，
一度認定是自己改的。實際上那是 **dispatcher 在 14:03 改的**，handler 的第一個編輯是 14:05。

`--stat` 為了對齊欄寬會截斷長路徑（印成 `.../middleware/main.py` 這種形式），
使得「我改的檔」與「別人改的檔」在同一份輸出裡**外觀無法區分**。

## 為什麼值得建檔

這不是排版瑕疵，是**共用工作樹下的歸屬判斷缺陷**。當多個 session 寫同一棵樹時：

| 想知道的 | `--stat` 能回答嗎 |
|---|---|
| 有哪些檔被改了 | 可以（但路徑可能被截斷） |
| **這些是誰改的** | **不能——而它看起來像能** |

具體危害：handler 若不查證就 commit，會把 dispatcher 的改動夾帶進自己的 commit，
兩段本應分離的變更被綁在同一個 sha 上。本輪之所以沒發生，**只是因為 handler 主動去查了**。

## 正確做法

**要完整路徑**：

```bash
git diff --name-only          # 不截斷，一行一個完整路徑
git status --porcelain        # 同樣不截斷，且帶狀態碼
```

**要判斷歸屬**（`git` 本身無法回答未 commit 改動的作者，必須靠外部證據）：

```bash
# 拿 mtime 對照自己開始工作的時間
stat -c '%y %n' <file>
# 交叉驗證：若改動已生效於容器，看容器 StartedAt
docker inspect -f '{{.State.StartedAt}} {{.Config.Image}}' <container>
```

這正是 handler 本輪實際採用的手法，值得沿用。

## 更根本的處方（dispatcher 側）

**這件事的真正根因在我，不在工具。** dispatcher 在 handler 工作期間改了同一棵樹的檔案
而**未告知 handler**。`coordinator-discipline` §B.2 要求第二條線必須把在飛線的檔案集
當作 do-not-touch list 交給對方——**反向也成立：dispatcher 自己動樹時同樣要通知在飛的 handler。**

## 歸責

工具側屬揭露缺陷：`--stat` 知道完整路徑（它就是從完整路徑截出來的），
但為了排版丟棄了資訊，且不標示自己截斷過。
流程側則是 dispatcher 的通報疏漏，已於遣散訊息中向 handler 認明。

**Related**: `BR_20260809_py_compile_permission_failure_shares_rc_with_syntax_error.md`
（同一顆 handler 同一輪揭露；同族：工具持有真相但以損失判別力的形式呈現）
