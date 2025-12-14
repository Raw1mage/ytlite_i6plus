# Development Progress

## Phase 1: Environment Setup
- [x] SSH Access configured (Key-based auth).
- [x] Python 3 environment verified.
- [x] `pip` installed via \`ensurepip\`.
- [x] Dependencies installed: \`flask\`, \`yt-dlp\`.
- [x] Git installed and repository initialized.

## Phase 2: Core Development
- [x] Basic Flask app structure created.
- [x] `yt-dlp` integration for video extraction.
- [x] Search functionality implemented.
- [x] Video playback interface (Safari native).
- [x] **Optimization:** Improve search speed (Combined yt-dlp calls, used os.popen).
- [x] **Feature:** Add "Load More" for search results.
- [x] **Feature:** Video quality selection (Fixed to best[ext=mp4] for Safari compatibility).
- [x] **UI:** Brand update to "Youtube Lite" & Dark Mode.
- [x] **Feature:** Header Search Bar with Magnifying Glass button.
- [x] **Feature:** Categories (Chips) - News, Live, Podcast.
- [x] **Feature:** Local Watch History.
- [x] **Feature:** Overlay Player (SPA-like experience).

## Phase 4: v2.1 Refinements (Pure PiP & Optimization)
- [x] **Feature:** Native Picture-in-Picture (PiP) Mode (Video Only, No Text).
- [x] **Feature:** Login & Subscriptions System (OAuth2).
- [x] **Feature:** Background Caching for Home Feed & Subscriptions.
- [x] **Feature:** Smart Resource Scheduling (Pause background tasks when user active).
- [x] **Feature:** Related Videos (Client-side recommendation).
- [x] **Feature:** Refresh Button for Home Feed.
- [x] **UX:** Direct Channel Navigation & Clickable Channel Links.
- [x] **UX:** Simplified Search Results Page.

## Known Issues (Blocking / Bugs)
- [!] **Device Instability:** iPhone 6 Plus (A8) experiences voltage sag (battery drop from 60% to 1%) and reboots under high load (Python backend + Video decoding), causing Jailbreak/SSH loss.
- [!] **Parsing Hangs:** "All" category sometimes gets stuck on "Parsing..." indefinitely. (Attempted fix: Promise.race timeout & Refresh button. Status: Verification blocked by device reboot).
- [ ] **Deployment Pending:** Latest code (Refresh logic) is committed but not deployed to device due to connection loss.
