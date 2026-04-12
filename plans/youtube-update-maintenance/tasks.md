# Tasks

## 1. 依賴升級（最小修復）

- [ ] 1.1 固定 `yt-dlp==2026.3.17` 於 `webbox/requirements.txt`
- [ ] 1.2 固定 Invidious image tag 於 `webbox/docker-compose.yml`（從 `latest` 改為穩定版本）
- [ ] 1.3 重建 Docker containers（`docker compose build && docker compose up -d`）

## 2. 驗證修復

- [ ] 2.1 確認 Invidious API 可回傳 `formatStreams`（`curl http://localhost:1215/api/v1/videos/{test_id}`）
- [ ] 2.2 確認串流播放正常（`/api/get_stream?v={test_id}` 回傳有效 stream_url）
- [ ] 2.3 確認下載功能正常（MP3/MP4 各測一次）

## 3. SOP 文件化

- [ ] 3.1 列出需要定期檢查的程式與部署檔
- [ ] 3.2 列出每週、故障時、改版後三種更新流程
- [ ] 3.3 列出驗收條件與回歸檢查方式

## 4. Validation

- [ ] 4.1 檢查 plan package 文件是否符合 planner skill 的必要欄位
- [ ] 4.2 檢查 SOP 是否可直接作為日常維護清單
