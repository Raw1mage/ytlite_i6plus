# Plan for Video Download & Playlist Management

This document outlines the implementation plan for adding playlist browsing and video downloading capabilities to YT Lite.

## 1. Overview
The goal is to allow users to browsing channel playlists, view playlist items, and download videos or entire playlists as MP3/MP4 files. The download process will be managed by a queue system on the backend.

## 2. Architecture Changes

### Backend (FastAPI Middleware)
*   **System Dependencies**: 
    *   Need `ffmpeg` installed in the Docker container for media conversion.
    *   Need `yt-dlp` python package.
*   **Data Models**:
    *   `DownloadJob`: Tracks ID, title, type (video/playlist), status (queued, downloading, converting, finished, error), progress (%), file path.
*   **Storage**: 
    *   Downloaded files will be stored in `/app/data/downloads` (mounted volume).
*   **New Modules**:
    *   `downloader.py`: Wrapper around `yt-dlp` to handle async downloads and progress hooks.
    *   `queue_manager.py`: (Optional) Simple in-memory queue or SQLite-backed job manager.

### API Endpoints
1.  `GET /api/channel/{channelId}/playlists`: Fetch playlists from Invidious.
2.  `GET /api/playlist/{playlistId}`: Fetch playlist details and videos.
3.  `POST /api/download`: Submit a download request.
    *   Body: `{ id: str, type: 'video'|'playlist', format: 'mp3'|'mp4' }`
4.  `GET /api/downloads`: Get status of all active/recent downloads.
5.  `POST /api/downloads/{jobId}/cancel`: Cancel a download.
6.  `DELETE /api/downloads/{jobId}`: Remove file and record.

### Frontend (UI/UX)
*   **Universal Selection Mode**:
    *   Allow entering "Selection Mode" (via long-press on mobile or specific button).
    *   **Keyboard Support**: Support `Ctrl/Cmd + Click` (toggle selection) and `Shift + Click` (range selection) on Desktop.
    *   **Visual Feedback**: Selected video cards will have a distinct highlight (border/overlay) and a checkmark.
    *   **Action Bar**: A floating bottom bar appears when items are selected, offering:
        *   Download Selected (MP3 / MP4).
        *   Add to Playlist (Future).
        *   Clear Selection.
*   **Channel Page**: Add "Playlists" tab/section.
*   **Playlist Page**: New view showing list of videos.
*   **Download Manager Page** (`/downloads`): 
    *   Inspired by ByClick Downloader.
    *   List view of active downloads with progress bars.
    *   History of completed downloads with direct fetch links.

## 3. Implementation Steps

### Phase 1: Environment & Backend Basics
1.  **Update `webox/BUILD/middleware/Dockerfile`**:
    *   Install `ffmpeg` (apt-get).
2.  **Update `requirements.txt`**:
    *   Add `yt-dlp`.
3.  **Implement `downloader.py`**:
    *   Basic class to run `yt-dlp` in a separate thread/process.
    *   Callback for progress updates.

### Phase 2: Core API & State Management
1.  **Download Job Manager**:
    *   In-memory dictionary `jobs = {}` for MVP.
    *   Background task loop to process queue (limit concurrent downloads, e.g., 2).
2.  **API Implementation**:
    *   Implement `/api/download` endpoint.
    *   Implement `/api/downloads` polling endpoint.

### Phase 3: Playlist Browsing (Frontend + API)
1.  **API Proxy**:
    *   Add Invidious proxy endpoints for Playlists.
2.  **UI Implementation**:
    *   Update `channel.html` to show playlists.
    *   Create `playlist.html` to show items.

### Phase 4: Download UI & Integration
1.  **Download Manager UI**:
    *   Create `downloads.html`.
    *   Add JS polling to update progress bars.
2.  **Integration**:
    *   Add "Download" buttons on Video and Playlist pages.
    *   Ensure files are accessible (StaticFiles mount for `/downloads`).

## 4. Design Aesthetics
*   **Downloads Page**: Use a clean, table/card hybrid layout.
    *   **Active**: Animated progress bars (green/blue gradients).
    *   **Completed**: distinct "Check" icon, file size, and "Open" action.
*   **Glassmorphism**: Consistent with existing UI.

## 5. Risks
*   **Performance**: Video encoding (ffmpeg) is CPU intensive. On a low-power host (if applicable), this might slow down the web server. *Mitigation*: Limit concurrent conversions to 1.
*   **Storage**: Large files filling up disk. *Mitigation*: Show free space? (Out of scope for simple version).
