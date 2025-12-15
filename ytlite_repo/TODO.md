# Task List for YT Lite

## Backend / API
- [ ] **Fix Related Videos Data**: Update `main.py` (`/api/get_stream`) to include `recommendedVideos` from the Invidious API response instead of ignoring it.
- [ ] **Fix Player Title Loading**: Ensure the player title is correctly updated from the API response when opening a video via a direct link (currently relies on placeholder or incomplete data).

## Frontend / UI
- [ ] **Implement Related Videos UI**: Update `base.html` (`openPlayer`) to render the "Next Up" list using the data from the API (`recommendedVideos`) instead of scraping the background DOM.
- [ ] **Fix Player Spacing (The "Ghost" Gap)**: 
    - Investigate and fix the large gap between the video and text.
    - Change `.video-section` and `.video-wrapper` from fixed `60vh` height to a responsive aspect ratio (e.g., `aspect-ratio: 16/9`) to avoid excessive whitespace.
- [ ] **Fix Unclickable Header**:
    - Debug z-index or positioning overlap preventing header button clicks when the player overlay is open (especially from search results).
    - Check if `overlay-container` is inadvertently covering the header.
- [ ] **Fix Back Button Navigation**:
    - Implement `window.onpopstate` handling in `base.html`.
    - Ensure pressing "Back" closes the player overlay and returns to the previous state (e.g., Search Results or Home) instead of just changing the URL while keeping the player open.
