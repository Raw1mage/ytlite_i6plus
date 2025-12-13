# YT Lite (iPhone 6 Plus Edition)

## Project Overview
A lightweight, self-hosted YouTube proxy designed specifically for legacy iOS devices (like the iPhone 6 Plus on iOS 12.5.7). 
It runs **on-device** using Python Flask and yt-dlp, serving a stripped-down HTML interface to Mobile Safari.

## Architecture
- **Hardware:** iPhone 6 Plus (A8, 1GB RAM)
- **OS:** iOS 12.5.7 (Jailbroken via checkra1n)
- **Backend:** Python 3.9 (Flask)
- **Core Engine:** `yt-dlp` (Extracts direct MP4 stream URLs)
- **Frontend:** HTML5 + Jinja2 (No heavy JS frameworks)
- **Playback:** Native iOS Safari `<video>` player (Hardware Accelerated)

## Installation
1.  **Dependencies:**
    - Python 3
    - `pip` (bootstrapped via `ensurepip`)
    - `flask`, `yt-dlp`
    - `git`
2.  **Setup:**
    \`\`\`bash
    git clone <repo_url>
    cd yt_lite
    python3 app.py
    \`\`\`
3.  **Usage:**
    Open Safari and navigate to \`http://localhost:5000\`.
    Tap "Share" -> "Add to Home Screen" for a fullscreen app experience.
