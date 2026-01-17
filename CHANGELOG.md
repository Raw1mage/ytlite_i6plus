# Changelog

All notable changes to this project will be documented in this file.

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
