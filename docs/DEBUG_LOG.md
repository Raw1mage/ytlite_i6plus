# Debug Log - YT Lite v3 Refactor

**Session ID**: 2025-12-14_v3_refactor  
**Timestamp**: 2025-12-14T21:45:00+08:00  
**Phase**: Video Feed Implementation  
**Status**: ✅ SUCCESS

---

## Issues Summary

| ID | Severity | Title | Status | Resolved At |
|----|----------|-------|--------|-------------|
| UI-001 | High | Header Content Overlap | ✅ RESOLVED | 21:15 |
| UI-002 | Medium | Header Layout Not Following Conventions | ✅ RESOLVED | 21:20 |
| UI-003 | High | Header Appearing at Bottom | ✅ RESOLVED | 21:38 |
| INFRA-001 | **Critical** | Invidious API 500 Errors | ✅ RESOLVED | 21:30 |
| INFRA-002 | Medium | Port 3000 Conflict | ✅ RESOLVED | 21:27 |
| INFRA-003 | High | Thumbnails Not Displaying | ✅ RESOLVED | 21:42 |
| INFRA-004 | Medium | Content Language Mismatch | ✅ RESOLVED | 21:40 |
| CODE-001 | High | Function Name Mismatch | ✅ RESOLVED | 21:35 |
| AUTH-001 | Medium | OAuth Scope Mismatch | ✅ RESOLVED | 20:58 |
| DEP-001 | High | Missing itsdangerous | ✅ RESOLVED | 20:52 |
| DEP-002 | Low | Missing Response Import | ✅ RESOLVED | 21:05 |

**Metrics**: 11/11 resolved (100% success rate)

---

## Detailed Issue Reports

### UI-001: Header Content Overlap ⚠️ High
**Problem**: Category chips (全部, 新聞, etc.) were hidden behind fixed header

**Root Cause**: `position: fixed` header with insufficient `body { padding-top: 60px }`

**Symptoms**:
- Blank page below header
- Category buttons only half visible
- Content appearing under header on scroll

**Solution**: Changed from `position: fixed` to `position: sticky` with Flexbox layout

**Changes**:
- `base.html`: Changed header from fixed to sticky
- `base.html`: Removed body padding-top
- `base.html`: Added flex layout to body
- `base.html`: Reduced header padding from 10px to 8px
- `index.html`: Added margin-top to chips-container

**Status**: ✅ RESOLVED (2025-12-14 21:15)

---

### UI-002: Header Layout Not Following Conventions 📐 Medium
**Problem**: Search box and login should be on the right, but category chips were in wrong position

**Root Cause**: Category chips were in page content instead of header

**Solution**: Moved chips-container into header, reorganized flex layout

**New Layout**: `[Logo] [Chips] ─── [Search] [Login]`

**Changes**:
- `base.html`: Moved chips from index.html into header
- `base.html`: Reorganized header flex structure
- `index.html`: Removed duplicate chips-container

**Status**: ✅ RESOLVED (2025-12-14 21:20)

---

### UI-003: Header Appearing at Bottom of Page ⚠️ High
**Problem**: Header was displaying at bottom instead of top due to incorrect HTML element ordering

**Root Cause**: Header element was placed after drawer and overlay in HTML structure

**Solution**: Reorganized body structure to place header first

**Correct Order**:
```html
<body>
  <header>...</header>      <!-- ✅ First -->
  <drawer>...</drawer>
  <overlay>...</overlay>
  <container>...</container>
</body>
```

**Changes**:
- `base.html`: Moved header before drawer and overlay elements

**Status**: ✅ RESOLVED (2025-12-14 21:38)

---

### INFRA-001: Invidious API Returning 500 Errors 🔴 Critical
**Problem**: `/api/v1/trending` endpoint returns 500 Internal Server Error

**Root Cause**: YouTube blocking `/trending` endpoint due to anti-scraping measures

**Symptoms**:
- Empty video feed
- Logs show: `500 GET /api/v1/trending?region=TW`
- Warning: "Invidious companion is required"

**Investigation**:
- ✅ Invidious web UI works (returns 200 OK)
- ✅ Database connection successful
- ✅ `/api/v1/search` endpoints work reliably
- ❌ `/api/v1/trending` blocked by YouTube

**Solution**: Changed from `/trending` to `/search` with Traditional Chinese keywords

**Changes**:
```python
# Before
url = f"{INVIDIOUS_API_URL}/api/v1/trending?region=TW"

# After
url = f"{INVIDIOUS_API_URL}/api/v1/search?q=台灣熱門&sort_by=relevance&type=video"
```

**Category Mappings**:
- **全部**: `q=台灣熱門&sort_by=relevance`
- **新聞**: `q=台灣新聞&sort_by=upload_date`
- **直播**: `q=台灣直播&features=live`
- **Podcast**: `q=中文podcast`

**Status**: ✅ RESOLVED (2025-12-14 21:30)

---

### INFRA-002: Port 3000 Conflict 🔌 Medium
**Problem**: Invidious couldn't bind to port 3000 - already in use by Node.js service

**Root Cause**: Hexapod Simulator running on port 3000

**Solution**: Sequential port allocation starting from 1214

**Port Allocation**:
- **1214**: YT Lite Web Interface (Middleware)
- **1215**: Invidious API
- **1216**: PostgreSQL (for debugging)

**Changes**:
- `docker-compose.yml`: Changed ports from `3000:3000` to `1215:3000`
- `docker-compose.yml`: Added PostgreSQL port mapping `1216:5432`

**Status**: ✅ RESOLVED (2025-12-14 21:27)

---

### INFRA-003: Video Thumbnails Not Displaying 🖼️ High
**Problem**: All video thumbnails showing as broken images

**Root Cause**: Invidious returning internal Docker network URLs (`http://invidious:3000`) that browsers cannot access

**Example**:
```
❌ http://invidious:3000/vi/IFUo3G_51HQ/maxres.jpg  (internal)
✅ http://localhost:1215/vi/IFUo3G_51HQ/maxres.jpg  (external)
```

**Solution**: Replace internal Docker URLs with external localhost URLs

**Changes**:
```python
# Fix internal Docker URLs
if 'invidious:3000' in thumb:
    thumb = thumb.replace('http://invidious:3000', 'http://localhost:1215')
# Fix relative URLs
elif thumb.startswith('/'):
    thumb = f"http://localhost:1215{thumb}"
# Fallback to YouTube CDN
if not thumb:
    thumb = f"https://i.ytimg.com/vi/{item['videoId']}/hqdefault.jpg"
```

**Status**: ✅ RESOLVED (2025-12-14 21:42)

---

### INFRA-004: Content Language Mismatch 🌐 Medium
**Problem**: All video content was in English instead of Traditional Chinese

**Root Cause**: Search queries using English keywords (`popular`, `news`, etc.)

**Solution**: Changed search queries to Traditional Chinese keywords

**Keyword Changes**:
- `popular` → `台灣熱門`
- `Taiwan news` → `台灣新聞`
- `live` → `台灣直播`
- `podcast` → `中文podcast`

**Status**: ✅ RESOLVED (2025-12-14 21:40)

---

### CODE-001: Function Name Mismatch ⚙️ High
**Problem**: Category chips calling `loadCategory()` but function defined as `selectCategory()`

**Root Cause**: Inconsistent naming between `base.html` and `index.html`

**Solution**: Renamed function to match caller

**Changes**:
- `index.html`: Renamed `selectCategory` to `loadCategory`

**Status**: ✅ RESOLVED (2025-12-14 21:35)

---

### AUTH-001: OAuth Scope Mismatch Warning 🔐 Medium
**Problem**: Google returns more scopes than requested, causing oauthlib to throw Warning

**Root Cause**: oauthlib strict scope validation

**Solution**: Set `OAUTHLIB_RELAX_TOKEN_SCOPE=1` environment variable

**Changes**:
```python
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
```

**Status**: ✅ RESOLVED (2025-12-14 20:58)

---

### DEP-001: Missing Python Dependency 📦 High
**Problem**: `ModuleNotFoundError: No module named 'itsdangerous'`

**Root Cause**: SessionMiddleware requires itsdangerous but it wasn't in requirements.txt

**Solution**: Added itsdangerous to requirements.txt

**Changes**:
```txt
google-api-python-client
sqlalchemy
itsdangerous  # ← Added
```

**Status**: ✅ RESOLVED (2025-12-14 20:52)

---

### DEP-002: Missing Response Import 📥 Low
**Problem**: Used `Response` type in function signature without importing it

**Root Cause**: Incomplete import statement

**Solution**: Added Response to fastapi.responses imports

**Changes**:
```python
from fastapi.responses import HTMLResponse, RedirectResponse, Response
```

**Status**: ✅ RESOLVED (2025-12-14 21:05)

---

## Deployment Status

### Services
| Service | Status | Port |
|---------|--------|------|
| PostgreSQL | 🟢 Healthy | 1216 |
| Invidious | 🟢 Healthy | 1215 |
| Middleware | 🟢 Healthy | 1214 |

### Endpoints
| Endpoint | Status | Description |
|----------|--------|-------------|
| `http://localhost:1214` | 🟢 Accessible | Video feed working |
| `https://ytlite.sob.com.tw` | 🟢 Accessible | Via Nginx reverse proxy |
| `http://localhost:1215` | 🟢 Accessible | Invidious API |
| `http://localhost:1216` | 🟢 Accessible | PostgreSQL |

### Features
| Feature | Status |
|---------|--------|
| Video Feed | ✅ Working |
| Thumbnails | ✅ Working |
| Categories | ✅ Working |
| Search UI | ✅ Ready |
| OAuth Login | ✅ Working |

---

## Achievements 🎉

1. ✅ **First page fully functional** with video grid
2. ✅ **Traditional Chinese content** localization
3. ✅ **All thumbnails displaying** correctly
4. ✅ **Clean UI** with proper layout
5. ✅ **Sequential port allocation** (1214-1216)
6. ✅ **All 11 critical bugs resolved**

---

## Next Steps

1. **Implement video playback** - Click on video to play
2. **Add subscription feed** - Display user's subscribed channels
3. **Implement search functionality** - Make search box functional
4. **Add watch history** - Store in localStorage
5. **Optimize performance** - Lazy loading, infinite scroll

---

*Last Updated: 2025-12-14 21:45:00 +08:00*
