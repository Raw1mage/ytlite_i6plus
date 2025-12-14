# YT Lite v3 Development Progress

## Project Overview
Refactoring YT Lite into a Dockerized microservices architecture for PC hosting, enabling personalized YouTube experiences for legacy devices.

## Architecture
- **Backend**: Invidious (scraping engine) + Python FastAPI (middleware)
- **Frontend**: PWA (Progressive Web App) optimized for iPhone 6 Plus
- **Database**: PostgreSQL
- **Deployment**: Docker Compose on powerful PC

## Completed Milestones

### Phase 1: Infrastructure Setup ✅
- [x] Docker Compose configuration with 3 services (Postgres, Invidious, Middleware)
- [x] Port configuration (1214 for middleware, 3001 for Invidious)
- [x] Volume mounts for persistent data
- [x] `webctl.sh` management script
- [x] Project structure reorganization (src/, BUILD/, refs/, docs/HISTORY/)

### Phase 2: Middleware Core ✅
- [x] FastAPI application with Jinja2 templates
- [x] Google OAuth2 flow implementation
- [x] Session management with cookies
- [x] Proxy headers middleware for HTTPS support
- [x] API endpoints:
  - `/` - Home page with login status
  - `/login` - OAuth initiation
  - `/oauth2callback` - OAuth callback handler
  - `/logout` - Session cleanup
  - `/api/videos` - Video feed proxy
  - `/api/subscriptions` - User subscriptions sync
  - `/api/get_stream` - Video stream URL resolver

### Phase 3: UI Refactoring ✅ (2025-12-14)
- [x] Fixed header layout using `position: sticky` instead of `fixed`
- [x] Eliminated content overlap issues
- [x] Reorganized header structure:
  - Left: Hamburger menu + Logo
  - Center: Category chips (全部, 新聞, 直播, etc.)
  - Right: Search box + Login/Logout
- [x] Reduced header padding for compact design (8px vertical)
- [x] Flexbox-based layout for natural element flow
- [x] No-cache headers to prevent browser caching issues
- [x] Mobile-responsive design maintained

## Current Status

### Working Features
✅ **UI/UX**
- Clean, non-overlapping header layout
- Category navigation chips
- Search functionality (UI ready)
- Login/Logout buttons with proper styling
- Drawer navigation menu
- Responsive design

✅ **Authentication**
- Google OAuth2 login flow
- Session persistence
- Token storage in `/app/data/token.json`

✅ **Infrastructure**
- Docker services running
- Port mapping (1214 → middleware, 3001 → Invidious)
- HTTPS support via Nginx reverse proxy (`https://ytlite.sob.com.tw`)

### Known Issues

❌ **Invidious API**
- Local Invidious instance returns 500 errors on `/api/v1/trending`
- Port 3000 conflict resolved (moved to 3001)
- Database connection established but API endpoints not responding
- Possible causes:
  - Invidious needs initialization time
  - YouTube anti-scraping measures
  - Configuration issues
  - Missing Invidious Companion service

❌ **Video Feed**
- `/api/videos` returns empty array
- Frontend displays blank video grid
- Public Invidious instances have API disabled

## Next Steps

### Immediate (Critical Path)
1. **Fix Invidious API**
   - Option A: Debug local Invidious configuration
   - Option B: Use mock data for UI testing
   - Option C: Try different Invidious Docker image version

2. **Complete Video Playback**
   - Test `/api/get_stream` endpoint
   - Implement video player overlay
   - Add related videos sidebar

3. **Subscription Features**
   - Test `/api/subscriptions` with real Google account
   - Display subscription list in drawer
   - Implement subscription feed

### Future Enhancements
- [ ] Search functionality
- [ ] Watch history (localStorage)
- [ ] Playlist management
- [ ] Comments section
- [ ] Video quality selector
- [ ] Offline mode (PWA)
- [ ] Push notifications

## Technical Decisions

### Why Sticky Instead of Fixed Header?
- **Before**: `position: fixed` with `body { padding-top: 60px }`
  - Required manual calculation of header height
  - Content overlap when header height changed
  - Multiple z-index layers causing confusion

- **After**: `position: sticky` with Flexbox
  - Header naturally flows with content
  - No overlap issues
  - Simpler CSS, easier to maintain
  - Header sticks to top only when scrolling

### Why Port 3001 for Invidious?
- Port 3000 was occupied by another Node.js service (Hexapod Simulator)
- Changed Docker mapping from `3000:3000` to `3001:3000`
- Internal container still uses 3000, external access via 3001

### Why Separate Middleware?
- Handles OAuth (Invidious doesn't support Google login)
- Merges data from multiple sources (Invidious + Google API)
- Provides unified API for frontend
- Easier to add features without modifying Invidious

## Environment

### Development
- **OS**: Linux
- **Docker**: Docker Compose v2
- **Python**: 3.10
- **Node**: v16+ (for other services on same machine)

### Production
- **Domain**: `https://ytlite.sob.com.tw`
- **Reverse Proxy**: Nginx
- **SSL**: Enabled
- **Data Volume**: `/opt/ytlite_v3/`

## Lessons Learned

1. **CSS Layering**: Avoid `position: fixed` unless absolutely necessary. `sticky` is often a better choice.
2. **Port Conflicts**: Always check for port conflicts before deploying (`netstat -tulpn`).
3. **Docker Caching**: Use `--rebuild` flag when code changes aren't reflected.
4. **OAuth Redirects**: Must match exactly in Google Cloud Console, including protocol (http vs https).
5. **Browser Caching**: Set `Cache-Control: no-cache` for development to avoid stale content.

## References
- [Invidious Documentation](https://docs.invidious.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google OAuth2 Guide](https://developers.google.com/identity/protocols/oauth2)
