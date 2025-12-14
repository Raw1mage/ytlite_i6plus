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
    ```bash
    git clone <repo_url>
    cd yt_lite
    python3 app.py
    ```
3.  **Usage:**
    Open Safari and navigate to `http://localhost` (Port 80).
    Tap "Share" -> "Add to Home Screen" for a fullscreen app experience.

## Features (v2.1)
- **Smart Background Caching:** Pre-fetches subscriptions and home feed for instant loading. Includes resource scheduling to pause during playback.
- **Pure PiP Mode:** Native iOS Picture-in-Picture window without text or clutter.
- **Login & Subscriptions:** Full OAuth2 integration to view personal subscription feeds.
- **Related Videos:** Smart client-side recommendations based on current list.
- **Optimization:** Direct mp4 extraction optimized for legacy iOS (720p limit, Timeout protection).

## Known Issues & Troubleshooting
### 1. Battery & Reboot Issues (Critical)
The iPhone 6 Plus (A8 chip) may experience "Voltage Sag" under high load (running backend + playing video), causing the battery to report 1% or the device to reboot unexpectedly.
**Solution:** 
- Always keep the device plugged into a reliable power source (iPad 12W charger recommended).
- Allow the device to cool down if it overheats.

### 2. "Parsing..." Stuck Loop
Occasionally, the "All" category or search results may get stuck on "Parsing...".
**Solution:**
- Click the **"↻ Refresh"** button in the category bar (v2.1+).
- If persistent, verify internet connection or restart the Python server.

### 3. SSH/Jailbreak Loss
If the device reboots, the jailbreak state is lost.
**Solution:**
- Re-run the Jailbreak tool (unc0ver/checkra1n).
- Re-enable OpenSSH.
- Restart the YT Lite server: `python3 app.py`
