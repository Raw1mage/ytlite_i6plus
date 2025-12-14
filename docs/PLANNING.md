# Project Planning: YT Lite v3 (The Fusion)

## 1. Executive Summary
Build a high-performance, self-hosted YouTube client that combines the scraping power of **Invidious** with the personalized user experience of **YouTube Official**, optimized for legacy application (iOS/Android).

**Core Philosophy:** "Your Data, Google's Content, Private Infrastructure."

---

## 2. System Architecture

The system is composed of three distinct layers running in a Dockerized environment.

```mermaid
graph TD
    subgraph "Client Layer (Legacy Devices)"
        iOS[iPhone 6 Plus (Safari PWA)]
        Android[Old Android (Chrome PWA)]
    end

    subgraph "Server Layer (Docker Host)"
        Frontend[YT Lite v3 Middleware (Python/FastAPI)]
        DB[(User DB - SQLite/Redis)]
        Invidious[Invidious Instance (The Engine)]
        Postgres[(Invidious DB)]
    end

    subgraph "External Cloud"
        GoogleAPI[Google Data API v3]
        YouTube[YouTube Video Servers]
    end

    iOS -->|HTTPS / JSON| Frontend
    Android -->|HTTPS / JSON| Frontend
    
    Frontend -->|Auth & Sync| GoogleAPI
    Frontend -->|Video Data & Search| Invidious
    Frontend -->|User Prefs| DB
    
    Invidious -->|Scraping| YouTube
    Frontend -->|Proxy Stream (Optional)| YouTube
```

### Module Responsibilities

1.  **Invidious (The Engine)**
    *   **Role**: Raw Data Provider.
    *   **Function**: Handles video extraction, captchas, cipher decryption, and search scraping.
    *   **Interface**: Local REST API (e.g., `http://invidious:3000/api/v1/...`).
    *   **Why**: Removes the burden of maintaining `yt-dlp` manually and handling anti-scraping logic.

2.  **YT Lite Middleware (The Brain)**
    *   **Role**: Orchestrator & Personalization Layer.
    *   **Tech**: Python (FastAPI or Flask).
    *   **Function**:
        *   **Auth Bridge**: Handles Google OAuth2 for users to "Login" with their real accounts.
        *   **Sync Engine**: Fetches user's *Subscriptions* and *Home Feed Recommendations* from Google API.
        *   **Data Fusion**: Merges Google's lists (IDs) with Invidious's rich metadata.
    *   **Why**: Invidious is anonymous; this layer brings the "Personalized YouTube" experience back.

3.  **Client Frontend (The Skin)**
    *   **Role**: Presentation Layer.
    *   **Tech**: HTML5 + Vanilla JS (SPA) + PWA.
    *   **Design Goal**: Pixel-perfect clone of YouTube Mobile App (Dark Mode).
    *   **Optimization**: Zero-dependency, HW-accelerated playback (`<video>`).

---

## 3. Key Feature Specifications

### 3.1. Personalized Login (The bridge)
*   **The Problem**: Invidious doesn't know who you are.
*   **The Solution**:
    1.  User clicks "Login with Google" on YT Lite.
    2.  Middleware performs OAuth2 flow (Server-side).
    3.  Middleware stores OAuth Token securely in its own DB.
    4.  **Sync**: Middleware calls `youtube.subscriptions.list` and `youtube.activities.list` (Recommendations) using the token.
    5.  **Display**: Middleware takes the Video IDs returned by Google, and asks Invidious for the video details (streams/thumbnails) to display to the user.
    *   *Result*: User sees their *actual* YouTube feed, but watches it anonymously via Invidious logic.

### 3.2. Docker Deployment
*   Single `docker-compose.yml` orchestrating:
    *   `invidious-db` (Postgres)
    *   `invidious` (The scraping engine)
    *   `yt-lite-web` (Your Middleware + Frontend)
*   Exposes one port (e.g., 8080) for all client access.

### 3.3. UI Recreation
*   **Home Tab**: Algorithm-driven feed (sourced from Google API).
*   **Shorts Tab**: Vertical scroll interface (filtered from feed).
*   **Library Tab**: History & Playlists (stored locally or synced).
*   **Player UI**: Overlay player, minimized view, gesture controls.

---

## 4. Implementation Roadmap

### Phase 1: Foundation (Docker & Invidious)
1.  Set up `docker-compose` with a working Invidious instance.
2.  Verify Invidious API access (`curl localhost:3000/api/v1/trending`).
3.  Scaffold the Python Middleware (FastAPI/Flask) to proxy requests to Invidious.

### Phase 2: The "Skin" (Frontend Upgrade)
1.  Migrate existing YT Lite HTML/JS to the new Middleware.
2.  Refactor Frontend to fetch data from Middleware (which proxies Invidious), replacing `yt-dlp` calls.
3.  **Milestone**: Working anonymous YouTube player on iOS.

### Phase 3: The "Brain" (Auth & Sync)
1.  Implement Google OAuth2 flow in Middleware.
2.  Create database schema for Users/Tokens.
3.  Implement `SyncService`: Fetch Subscriptions/HomeFeed from Google API.
4.  **Milestone**: User can login and see their real subscriptions.

### Phase 4: UI Polish & Optimization
1.  Implement "Infinite Scroll" for Home Feed.
2.  Add "Shorts" UI support (Vertical aspect ratio handling).
3.  PWA manifest tuning (App icon, splash screen).
4.  Performance tests on iPhone 6 Plus.

---

## 5. Technical Stack

*   **Backend**: Python 3.9+ (FastAPI recommended for async performance)
*   **Engine**: Invidious (Crystal)
*   **DB**: SQLite (Simple/Portable) or PostgreSQL (Robust)
*   **Frontend**: HTML5, CSS3 (Flexbox/Grid), Vanilla JS (ES6)
*   **Container**: Docker & Docker Compose

