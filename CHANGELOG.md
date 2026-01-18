# Changelog

All notable changes to this project will be documented in this file.
## [0.3.3] - 2026-01-18
### Added
- **Dynamic Playlist**: Automatically generates a playlist context when a video is played from any grid (Search Results, Channel Videos, History, etc.), enabling continuous auto-play of the visible list.

## [0.3.4] - 2026-01-18
### Added
- **Continuous Fullscreen (Mobile)**: Implemented "Immersive Mode" with a custom bottom-right button to allow continuous playback across playlist videos without exiting fullscreen layout.
- **Native Fullscreen (Local Player)**: Added support for true native fullscreen (`requestFullscreen`/`webkitEnterFullscreen`) when playing downloaded files on mobile.

### Fixed
- **Mobile Controls**: Removed the custom "Paused" overlay mask on mobile devices to ensure native YouTube player controls (progress bar, settings) are always accessible.
- **Mobile Landscape**: Fixed video aspect ratio in landscape mode to adapt to screen height (`85vh`), preventing "flat/stretched" video rendering.
- **Fullscreen Button**: Restored the native YouTube fullscreen button (`fs=1`) on all devices while offering the custom continuous-play button as an alternative.
- **Z-Index Layering**: Corrected z-index stacking for local video player to ensure custom overlay buttons are clickable.

## [0.3.2] - 2026-01-18
### Added
- **Range Selection**: Implemented `Shift+Click` functionality to select multiple video cards in a range (A to B) in the video list.


## [0.3.1] - 2026-01-18
### Added
- **Smart Cache System**: Implemented dedicated `/cache` directory with 100MB LRU eviction.
- **File Reuse**: System checks both downloads and cache to prevent redundant downloads.
- **Job Deduplication**: Prevents duplicate entries in download manager.

### Changed
- **UI Layout**: 
    - Moved "Next Up" section upwards (zero gap).
    - Removed collapse toggle for "Next Up" (always visible).
    - Changed description toggle to floating absolute position.
- **API**: Filtered out cache jobs from `/api/downloads`.

## [0.3.0] - 2026-01-18

### Fixed
- **Proxy Player**: Fixed download timeout notification showing up falsely after successful playback.
- **Proxy Player**: Fixed control bar interactivity issues on abnormal videos.
- **Playback**: Fixed black screen issues when switching between abnormal (proxy) and normal videos.
- **Playback**: Fixed infinite loading spinner on normal video playback.
- **Playlist**: Restored auto-play functionality for both standard and proxy players in mixed playlists.
- **UI**: Fixed "Ghost Bar" visual glitch in video description section.
- **UI**: Improved "Download" modal behavior and loading states.
- **UX**: Fixed issue where video description toggle area occupied space even when collapsed.

### Changed
- Refactored `openPlayer` logic to robustly handle YouTube Iframe recreation and styling (Z-Index/Positioning).
- Optimized description toggle button placement and styles.
- Enhanced `switchToProxyPlayer` to handle playback events for seamless playlist continuation.
