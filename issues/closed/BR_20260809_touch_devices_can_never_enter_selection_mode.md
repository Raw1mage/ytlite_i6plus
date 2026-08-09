# BR: 觸控裝置永遠無法進入多選模式，Download MP3/MP4 按鈕在 iPhone 上不可達

**Filed**: 2026-08-09
**Status**: OPEN
**Severity**: HIGH — 目標裝置就是 iPhone 6 Plus，此路徑等同功能不存在
**Owner**: unassigned
**Related**: `BR_20260809_download_jobs_in_memory_only_vanish_on_restart.md`（同一個「使用者看不到下載功能」的症狀，但那張是後端索引蒸發，這張是前端入口不可達——兩者獨立，各自都足以致命）

## 症狀

`base.html:796-801` 的「Download MP3」「Download MP4」按鈕永遠不會出現在 iPhone 上。

## 根因：進入選取模式的唯一鑰匙是鍵盤修飾鍵

`base.html:1336-1352`：

```js
const isMulti = e.ctrlKey || e.metaKey;      // 觸控裝置恆 false
const isRange = e.shiftKey;                   // 觸控裝置恆 false
const isSelectionActive = window.selectedVideos.size > 0;

if (isRange)                        { ... toggleSelection(...) }
else if (isMulti || isSelectionActive) { ... toggleSelection(...) }
else                                { /* Normal Click -> Open Player */ }
```

三個分支條件在觸控裝置上的取值：

| 條件 | iOS Safari 值 | 說明 |
|---|---|---|
| `e.ctrlKey` / `e.metaKey` | `false` | 觸控事件無修飾鍵 |
| `e.shiftKey` | `false` | 同上 |
| `isSelectionActive` | **`false`（初始）** | 這是自舉死結——它要求已經選了至少一個 |

**`isSelectionActive` 是唯一不需要鍵盤的分支，但它要求選取集合非空；而唯一能讓集合非空的方法，是先通過另外兩個需要鍵盤的分支。** 這是一個閉環：觸控裝置永遠停在 `else`，每次點擊都直接開播放器。

`selection-bar` 因此永遠停在 `bottom: -80px`（`base.html:793`，畫面外），`updateSelectionUI()`（1447-1455）的 `size > 0` 永遠不成立。

## 沒有任何替代入口

```bash
# 觸控多選的常見實作，逐一檢查（含控制組）
longpress    0
longPress    0
touchstart   1     # ← 唯一一處，在 1855 行，是播放器控制列，與選取無關
touchend     0
contextmenu  0
dblclick     0
# 控制組（證明 grep 會命中）：
ctrlKey      1     # 非 0
ZZZNOSUCH    0
```

`touchstart` 那一處：

```js
1855:  ['click', 'touchstart', 'mousemove'].forEach(evt => {
1856:      wrapper.addEventListener(evt, () => showImmersiveControls());
```

是 `.video-wrapper` 的沉浸式控制列，與選取無關。

**沒有長按、沒有右鍵、沒有雙擊、沒有「選取」模式切換按鈕。**

## 這解釋了 log 為何一次下載請求都沒有

```bash
grep -c '/api/download' <container log>   # → 0   (rc=1)
grep -c '/api/videos'   <container log>   # → 9   (rc=0，控制組)
```

不是使用者不想下載，是**前端根本發不出那個請求**。

## 建議修法

擇一或並行：

1. **給 `.video-card` 加長按進入選取**（`touchstart` + 500ms 計時器，`touchmove`/`touchend` 取消）——最貼近 iOS 使用者直覺。
2. **在工具列或分類列加一顆「選取」切換鈕**，按下後進入選取模式（設一個 `window.selectionMode = true`，讓 1339 的條件改讀它）——最簡單、最不依賴手勢相容性，且 iOS 12 上最穩。
3. 在每張 `.video-card` 角落放一個小 checkbox（僅在選取模式顯示）。

方案 2 成本最低且不碰觸控事件相容性，建議優先。

## 未量測

- 未在真機 iOS 12 Safari 上實測（Docker daemon 於調查期間死亡，見 `BR_20260809_docker_daemon_and_path_injection_vanish_together.md`）。以上為靜態程式碼推導 + log 佐證，但條件取值（觸控事件無 `ctrlKey`）屬 DOM 規格層事實，不依賴實測。

**Closed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n（dispatcher 獨立驗證 + live 生效確認）
