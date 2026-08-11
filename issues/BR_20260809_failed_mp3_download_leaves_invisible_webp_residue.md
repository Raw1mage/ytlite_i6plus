# BR: 下載失敗時留下的 .webp 縮圖是完全不可見的殘留

- **Status**: OPEN (low severity, introduced by the mp3-metadata change and accepted with eyes open)
**Triage**: 2026-08-11 by ses_01b36b5ffffeNy0N6OCtYnJm5n ([★]main) — OPEN — 已判定，低優先（每次失敗約 100KB 靜默堆積）
**Triage evidence**: REPRO（碼未動）：queue_manager.py:12 MEDIA_EXTS 仍不含 .webp；downloader.py:103 except → return False 無清理。現場 0 殘留僅因目錄於 2026-08-11 清空（釋放 306.5MB）。

- **Filed**: 2026-08-09 by ses_01b36b5ffffeNy0N6OCtYnJm5n (dispatcher, during verification of the mp3-metadata work package)
- **Component**: `webbox/src/middleware/downloader.py` (mp3 branch), `webbox/src/middleware/queue_manager.py:10` (`MEDIA_EXTS`)

## 症狀

mp3 下載加入 `'writethumbnail': True` 之後，yt-dlp 會先把縮圖寫成 `<video_id>.webp`，再由
`EmbedThumbnail` postprocessor 嵌進 mp3 並刪掉它。

**成功路徑會刪掉它。失敗路徑不會。** 於是每一次失敗的 mp3 下載，都在下載目錄留下一個
約 100KB 的 `.webp` 孤兒檔。

## 為什麼它是「不可見」的

三件事疊在一起，讓這個殘留沒有任何觀察窗口：

1. `MEDIA_EXTS`（`queue_manager.py:10`）不含 `.webp` ⇒ `rescan_download_dir()` 掃不到它，
   所以它永遠不會變成一個 job，UI 上不存在。
2. `downloader.py` 的 opts 帶 `quiet: True, no_warnings: True` ⇒ postprocessor 失敗完全靜默。
3. 下載失敗本身會被正常回報，但回報的是「下載失敗」，沒有任何欄位提到「而且留了一個檔」。

⇒ 使用者看到的是「下載失敗」，磁碟上實際發生的是「下載失敗 **且** 多了一個永不清除的檔案」。
兩者共用同一個可觀察輸出。

## 量測（可重跑）

在容器內，用 worktree 的 `downloader.py`：

```
REAL     (EmbedThumbnail 在)   → ['jNQXAC9IVRw.mp3']                  零殘留
NO_EMBED (移除 EmbedThumbnail) → ['jNQXAC9IVRw.mp3', 'jNQXAC9IVRw.webp']
MEDIA_EXTS 含 '.webp'          → False
```

`NO_EMBED` 是刻意製造的可控重現（移除整個 postprocessor dict，帶 `MUTATION_NOT_APPLIED` 斷言）。

**真實觸發**：驗證期間 `W-DwNBbkU20` 一次 `HTTP Error 403: Forbidden`，
目錄留下 `W-DwNBbkU20.webp` 而沒有 mp3。這不是人造情境，是上游擋下載時的自然結果。

## 為什麼接受而不當場修

- 使用者要的功能（title / artist / 封面）已完整驗證通過，這個殘留不影響它。
- 每次失敗約 100KB，且只在失敗時發生。
- 修法會動到 `downloader.py` 的失敗路徑，需要製造失敗來驗證，成本高於它造成的傷害。

## 修法選項（未實作，供未來）

1. `downloader.py` 在 `except` 分支掃 `target_dir` 清掉同 `video_id` 的非媒體副檔案 —— 最直接，
   但要小心不能誤刪並行 job 的檔（`outtmpl` 以 `video_id` 命名，同一支影片的並行下載會互撞）。
2. 把 `.webp` / `.jpg` / `.png` 加進 `MEDIA_EXTS` —— **不要這樣做**。那會讓 rescan 把縮圖掃成
   `archived` job，UI 出現一堆假的「檔案」。這是治標且製造新問題。
3. 拿掉 `quiet: True, no_warnings: True` 讓 postprocessor 失敗至少留下 log —— 不解決殘留，
   但讓它不再靜默。

## Related

- `issues/closed/BR_20260809_delete_endpoint_couples_list_removal_with_file_deletion.md`
  （同族：兩者都是「檔案系統的實際狀態與 UI 呈現的狀態脫鉤」。前者是刪太多，這張是留太多。）
- `docs/verification_control_group_three_layer_failure.md`
  （這張 BR 的偵測方式就是那份文件的第一層：缺席態與失敗態共用同一個輸出。
  「下載失敗」與「下載失敗且留了檔」在使用者可見的每一個介面上都長得一樣。）
