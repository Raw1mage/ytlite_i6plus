# BR_20260809: `python3 -m py_compile` 的權限失敗與語法失敗共用 rc=1，訊息裡有真因但 rc 不帶

**Status**: OPEN
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — OPEN — 已判定，是 root-owned-dirs 的子項（修父即消失）
**Triage evidence**: REPRO：py_compile → rc=1 `Permission denied: .../__pycache__/main.cpython-312.pyc`；控制組 ast.parse → SYNTAX_OK rc=0。錯誤訊息逐字指名 BR_root_owned_dirs 的目錄 ⇒ 嚴格因果父子，修 PYTHONDONTWRITEBYTECODE=1 或非 root 執行即消滅觸發條件。

**Filed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（ytlite 值星官）
**Reported-by**: ses_01aeeafd6ffeO3Js1AojHkn9zz（handler，主動揭露；即使它自己已繞過）
**Severity**: 中——**會產生反向結論**：把「檢查跑不起來」讀成「被檢查物壞了」
**Owner**: 未指派

## 現象

在 bind-mount 的專案目錄上跑 `python3 -m py_compile main.py` 得到 `rc=1`。
自然的讀法是「語法錯誤」。真因是 **`__pycache__` 目錄由容器內 root 建立，
宿主機使用者無寫入權限**，py_compile 寫 bytecode 被拒。

**該檔語法完全正確。**

## 為什麼值得建檔

兩個完全不同的失敗擠在同一個 rc 上：

| 情境 | rc |
|---|---|
| 語法真的有錯 | 1 |
| 語法正確，但寫 `__pycache__` 被拒 | **1** |

而這個檢查的**用途**正是「判斷語法對不對」——它在最需要判別力的那一格上判別力為零。

**那一格資訊系統當下有**：stderr 明明白白印著 `Permission denied`。
只是 rc 不帶這個區分，而只取 rc 是驗證腳本裡最常見的寫法。

## 正確做法

用**不寫 bytecode** 的檢查，讓它只回答語法問題：

```python
import ast, sys
src = open(sys.argv[1], encoding='utf-8').read()
ast.parse(src)          # 只解析，不落檔，不需要目錄寫入權
print("SYNTAX_OK")
```

控制組（證明這個檢查在該失敗時真的會失敗）：

```bash
printf 'def x(:\n' > "$XDG_RUNTIME_DIR/bad.py"
python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$XDG_RUNTIME_DIR/bad.py"
# 預期 rc=1 + SyntaxError；若這裡回 0，你的檢查本身壞了
```

若仍要用 `py_compile`，**必須同時取 stderr 而非只取 rc**，並在訊息含
`Permission denied` 時改判為「檢查未執行」而非「被檢查物有缺陷」。

## 同族擴散（不只 py_compile）

任何「執行時會產生副檔案」的檢查器都有這個形狀——副作用失敗與被檢查物失敗共用退出碼：

- `pytest` 寫 `.pytest_cache` 被拒
- `tsc` 寫 `.tsbuildinfo` 被拒
- 任何 linter 寫 cache 目錄被拒

通則：**檢查器的失敗必須能區分「我沒跑成」與「你有問題」**。

## 歸責

不是「執行者不夠仔細」。屬揭露缺陷（G13-harness-disclosure 族）：訊息裡有答案，
退出碼不帶它，而退出碼是自動化流程唯一會讀的那一格。

**Related**: `BR_20260809_git_diff_stat_truncates_paths_causing_attribution_error.md`
（同一顆 handler 同一輪揭露；同族：工具知道真相但用最令人安心的形式回答）
