# Changelog

All notable changes to this project will be documented in this file.
## [0.3.5] - 2026-01-19
### Fixed
- **Old Device Compatibility**: Resolved Critical UI and JavaScript issues for iPhone 5s (iOS 12 / Safari 12).
    - Fixed `z-index` layering issue where the header blocked the navigation menu.
    - Replaced incompatible "Optional Chaining" (`?.`) syntax with ES5-compatible checks to prevent script crashes.

## [0.3.3] - 2026-01-18
### Added
- **Dynamic Playlist**: Automatically generates a playlist context when a video is played from any grid (Search Results, Channel Videos, History, etc.), enabling continuous auto-play of the visible list.

## [0.3.4] - 2026-01-18
### Changed
- **Mobile Player Layout**: Optimized the video player overlay to prevent top content (filter chips) from obscuring the video. The secondary header now auto-hides when the player is active.
- **Controls Optimization**: Removed redundant custom fullscreen and minimize buttons in favor of a cleaner, native-controls-first approach.
- **Visuals**: Adjusted video card vertical positioning to ensure full visibility of the native YouTube controls (including the native fullscreen button).
- **Bug Fix**: Removed the "Minimize" feature that caused playlist logic issues and visual defects on mobile.

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
