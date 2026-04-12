# Spec

## Purpose

- 定義一套可重複使用的 YouTube 截取與相關依賴更新流程，確保失效時能快速排查與恢復。
- **立即修復**：升級 yt-dlp 與 Invidious 版本，使服務恢復正常。

## Requirements

### Requirement: 升級 yt-dlp 至穩定版

The system SHALL 在 `webbox/requirements.txt` 中固定 yt-dlp 版本為 `2026.3.17`。

#### Scenario: 重建後下載恢復

- **GIVEN** requirements.txt 已固定 `yt-dlp==2026.3.17`
- **WHEN** Docker image 重建完成
- **THEN** 下載功能恢復正常（MP3/MP4 均可下載）

### Requirement: 升級 Invidious 至穩定版

The system SHALL 在 `docker-compose.yml` 中將 Invidious image 從 `latest` 改為固定版本 tag。

#### Scenario: 重建後串流播放恢復

- **GIVEN** Invidious 使用固定穩定版本
- **WHEN** 容器啟動後存取 `/api/get_stream`
- **THEN** `formatStreams` 回傳有效串流 URL

### Requirement: 定期檢查依賴

The system SHALL 定期檢查 `yt-dlp`、Invidious、Docker image 與系統依賴是否需要更新。

#### Scenario: 每週維護

- **GIVEN** 維護者進行週期性檢查
- **WHEN** 打開 maintenance SOP
- **THEN** 能找到要檢查的依賴項與對應檔案

### Requirement: 故障排查

The system SHALL 在 YouTube 截取失效時，先判斷是套件、站點還是部署問題。

#### Scenario: 播放或下載失敗

- **GIVEN** 使用者回報 YouTube 截取失效
- **WHEN** 查看 log 與關鍵檔案
- **THEN** 可先確認是否需要更新 `yt-dlp` 或補強錯誤 log

### Requirement: 文件化更新面

The system SHALL 列出所有需要持續追蹤的程式與文件位置。

#### Scenario: 新人接手

- **GIVEN** 新維護者接手專案
- **WHEN** 讀取 plan package
- **THEN** 能知道哪些檔案是更新與診斷的主要目標

## Acceptance Checks

- yt-dlp 固定為 `2026.3.17`，Docker build 可成功。
- Invidious image 固定版本，容器可正常啟動。
- 播放與下載功能在容器重建後恢復。
- 可從文件直接列出更新清單。
- 可從文件直接列出故障排查順序。
- 可從文件直接列出驗收標準與需檢查檔案。

