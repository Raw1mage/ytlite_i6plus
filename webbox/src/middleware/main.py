from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.background import BackgroundTask
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
import os
import json
from googleapiclient.errors import HttpError
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

import uuid

from queue_manager import QueueManager

app = FastAPI()

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Trust X-Forwarded-* headers from Nginx
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*") # or specific IP

# Security: Session Key should be random in production
app.add_middleware(SessionMiddleware, secret_key="YOUR_SECRET_KEY_HERE")

# Config
INVIDIOUS_API_URL = os.getenv("INVIDIOUS_API_URL", "http://invidious:3000")
# Base URL for OAuth Redirect (Optional Override)
CLIENT_BASE_URL = os.getenv("CLIENT_BASE_URL", None)

# Data Volume mapped to /app/data in Docker
DATA_DIR = "/app/data"
CLIENT_SECRETS_FILE = os.path.join(DATA_DIR, 'client_secret.json')
# We can also look in root if not found in data
if not os.path.exists(CLIENT_SECRETS_FILE):
     CLIENT_SECRETS_FILE = "client_secret.json"

# TOKEN_PATH = os.path.join(DATA_DIR, 'token.json') # Removed for security: use session storage
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.force-ssl"]

# Server-side Session Storage
SESSION_DIR = os.path.join(DATA_DIR, 'sessions')
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR, exist_ok=True)

# User Data Storage (Blocked Channels, etc.)
USERS_DIR = os.path.join(DATA_DIR, 'users')
if not os.path.exists(USERS_DIR):
    os.makedirs(USERS_DIR, exist_ok=True)

def get_user_id(request: Request, creds):
    """
    Get stable User ID (My Channel ID) using cached session or API.
    """
    uid = request.session.get('user_youtube_id')
    if uid:
        return uid
    
    if not creds or not creds.valid:
        return None
        
    try:
        service = build('youtube', 'v3', credentials=creds)
        # Fetch 'mine' channel
        response = service.channels().list(part='id', mine=True).execute()
        items = response.get('items', [])
        if items:
            uid = items[0]['id']
            request.session['user_youtube_id'] = uid
            return uid
    except Exception as e:
        print(f"Failed to get user ID: {e}")
    return None

def get_user_blocklist(user_id):
    if not user_id: return {}
    path = os.path.join(USERS_DIR, f"{user_id}_blocked.json")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f) # {channel_id: channel_name}
        except:
            return {}
    return {}

def save_user_blocklist(user_id, data):
    if not user_id: return
    path = os.path.join(USERS_DIR, f"{user_id}_blocked.json")
    with open(path, 'w') as f:
        json.dump(data, f)

def filter_blocked(videos, blocklist):
    if not blocklist: return videos
    return [v for v in videos if v.get('channel_id') not in blocklist]

def save_creds_to_session(request: Request, creds):
    session_id = request.session.get('user_session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session['user_session_id'] = session_id
    
    file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
    with open(file_path, 'w') as f:
        f.write(creds.to_json())

def get_creds_from_session(request: Request):
    session_id = request.session.get('user_session_id')
    if not session_id:
        return None
        
    file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                info = json.load(f)
            return info
        except Exception:
            return None
    return None

def clear_session_creds(request: Request):
    session_id = request.session.get('user_session_id')
    if session_id:
        file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
    request.session.clear()

# Setup
app.mount("/static", StaticFiles(directory="static"), name="static")


# Downloads Mount
# Downloads Mount
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)
app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

# Cache Mount
CACHE_DIR = os.path.join(DATA_DIR, "cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")

# Queue Manager
queue_manager = QueueManager(DOWNLOADS_DIR, CACHE_DIR)

templates = Jinja2Templates(directory="templates")

def normalize_thumb(video_id: str, thumb_url: str) -> str:
    """
    Ensure thumbnails are reachable externally by preferring YouTube CDN (hqdefault) when local-only URLs are detected.
    Maxres 404s are common；hqdefault 比較穩定。
    """
    if not video_id:
        return thumb_url or ''
    if not thumb_url:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    if thumb_url.startswith('/') or 'invidious:3000' in thumb_url or 'localhost:1215' in thumb_url:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return thumb_url or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

def get_creds(request: Request):
    info = get_creds_from_session(request)
    if info:
        try:
            creds = Credentials.from_authorized_user_info(info, SCOPES)
            
            if creds and creds.expired and creds.refresh_token:
                print(f"[Auth] Access token expired, refreshing... (Session ID: {request.session.get('user_session_id')})")
                try:
                    creds.refresh(GoogleRequest())
                    save_creds_to_session(request, creds)
                    print("[Auth] Refresh successful")
                except Exception as refresh_err:
                    print(f"[Auth] Refresh FAILED: {refresh_err}")
                    return None
            
            return creds
        except Exception as e:
            print(f"Auth Error in get_creds: {e}")
            return None
    # print(f"[Auth] No session info found. ID: {request.session.get('user_session_id')}")
    return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, response: Response):
    # Force no-cache to prevent browser caching issues
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    
    response = templates.TemplateResponse("index.html", {"request": request, "logged_in": logged_in})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    return templates.TemplateResponse("privacy.html", {"request": request, "logged_in": logged_in})

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    return templates.TemplateResponse("terms.html", {"request": request, "logged_in": logged_in})

@app.get("/login")
async def login(request: Request):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: client_secret.json not found in /app/data/"
        
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    
    # Determined dynamically from request (thanks to ProxyHeadersMiddleware)
    # OR overridden by env var if things get tricky
    if CLIENT_BASE_URL:
        redirect_uri = f"{CLIENT_BASE_URL}/oauth2callback"
    else:
        redirect_uri = str(request.url_for('oauth2callback'))
        
    # Force HTTPS if behind proxy but request looks http (common issue)
    if "https://" in str(request.base_url) or request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = redirect_uri.replace("http://", "https://")

    flow.redirect_uri = redirect_uri
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent')
    
    request.session['state'] = state
    request.session['redirect_uri'] = redirect_uri
    return RedirectResponse(authorization_url)

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    state = request.session.get('state')
    if not state:
        return "Error: Session state missing."
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES, state=state)
    flow.redirect_uri = request.session.get('redirect_uri')
    
    # Use the authorization server's response to fetch the OAuth 2.0 token.
    authorization_response = str(request.url).replace('8080', '1214')
    # If using http, ensure library allows insecure
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    
    # Save credentials
    # Save credentials to session instead of file
    # Save credentials to session file
    save_creds_to_session(request, creds)
        
    return RedirectResponse("/")

import asyncio
import random

# ... (imports) ...

@app.get("/logout")
async def logout(request: Request):
    # if os.path.exists(TOKEN_PATH):
    #     os.remove(TOKEN_PATH)
    clear_session_creds(request)
    return RedirectResponse("/")

from googleapiclient.discovery import build

def fetch_subscriptions_internal(credentials, max_results=500):
    """Fetch user subscriptions from YouTube API."""
    try:
        service = build('youtube', 'v3', credentials=credentials)
        items = []
        next_page_token = None
        
        while len(items) < max_results:
            request = service.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=min(50, max_results - len(items)),
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get('items', []):
                items.append({
                    "title": item['snippet']['title'],
                    "channelId": item['snippet']['resourceId']['channelId'],
                    "thumbnail": item['snippet']['thumbnails']['default']['url']
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
        return items
    except Exception as e:
        print(f"Error fetching subscriptions: {e}")
        return []

@app.get("/api/subscriptions")
async def get_subscriptions(request: Request):
    creds = get_creds(request)
    if not creds or not creds.valid:
        return {"error": "Not logged in"}
    
    subs = fetch_subscriptions_internal(creds)
    return {"subscriptions": subs} # Return object to match frontend expectation

import pydantic

class SubscriptionAction(pydantic.BaseModel):
    action: str
    channelId: str

@app.post("/api/subscription_action")
async def subscription_action(request: Request, body: SubscriptionAction):
    creds = get_creds(request)
    if not creds or not creds.valid:
        return {"error": "Not logged in"}
    
    try:
        service = build('youtube', 'v3', credentials=creds)
        if body.action == 'subscribe':
            service.subscriptions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "resourceId": {
                            "kind": "youtube#channel",
                            "channelId": body.channelId
                        }
                    }
                }
            ).execute()
        elif body.action == 'unsubscribe':
            # Need to find subscription ID first
            sub_list = service.subscriptions().list(
                part="id",
                mine=True,
                forChannelId=body.channelId
            ).execute()
            
            for item in sub_list.get('items', []):
                service.subscriptions().delete(id=item['id']).execute()
        
        return {"status": "success"}
    except HttpError as e:
        # Robustly check for subscriptionDuplicate
        is_duplicate = False
        try:
            content = e.content.decode() if isinstance(e.content, bytes) else str(e.content)
            if "subscriptionDuplicate" in content:
                is_duplicate = True
            else:
                error_details = json.loads(content)
                reason = error_details.get("error", {}).get("errors", [{}])[0].get("reason")
                if reason == "subscriptionDuplicate":
                    is_duplicate = True
        except:
            if "subscriptionDuplicate" in str(e):
                is_duplicate = True

        if is_duplicate:
            return {"status": "success", "note": "Already subscribed"}
            
        print(f"Sub Action API Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Sub Action Error: {e}")
        return {"error": str(e)}

class BlockAction(pydantic.BaseModel):
    action: str # 'block' or 'unblock'
    channelId: str
    channelName: str = ""

@app.post("/api/block_channel")
async def block_channel(request: Request, body: BlockAction):
    creds = get_creds(request)
    if not creds: return {"error": "Not logged in"}
    
    user_id = get_user_id(request, creds)
    if not user_id: return {"error": "Could not identify user"}
    
    blocklist = get_user_blocklist(user_id)
    
    if body.action == 'block':
        blocklist[body.channelId] = body.channelName or "Unknown"
    elif body.action == 'unblock':
        if body.channelId in blocklist:
            del blocklist[body.channelId]
            
    save_user_blocklist(user_id, blocklist)
    return {"status": "success", "blocked": blocklist}

@app.get("/api/blocked_channels")
async def get_blocked_channels(request: Request):
    creds = get_creds(request)
    if not creds: return {"error": "Not logged in"}
    user_id = get_user_id(request, creds)
    return get_user_blocklist(user_id)

@app.get("/api/videos")
async def get_videos(request: Request, category: str = "all", pageToken: str = ""):
    """
    Proxy request to Invidious API.
    """
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    
    # Load Blocklist
    blocklist = {}
    if logged_in:
        user_id = get_user_id(request, creds)
        blocklist = get_user_blocklist(user_id)
    
    print(f"[get_videos] category={category}, logged_in={logged_in}, pageToken={pageToken}, blocked_count={len(blocklist)}")

    async with httpx.AsyncClient() as client:
        try:
            # PERSONALIZED FEED LOGIC
            feed_videos = []
            
            # If Logged In + Category All -> SHOW ONLY SUBSCRIPTIONS (Random Shuffle Feed)
            if category == 'all' and logged_in:
                # 1. Get Subscriptions
                subs = fetch_subscriptions_internal(creds, max_results=50)
                if subs:
                    # 2. Pick Random 10 Channels (Increased from 5 for better feed)
                    targets = random.sample(subs, k=min(len(subs), 10))
                    
                    # 3. Fetch Latest Videos Concurrently
                    tasks = []
                    for sub in targets:
                        url = f"{INVIDIOUS_API_URL}/api/v1/channels/{sub['channelId']}"
                        tasks.append(client.get(url))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for res in results:
                        if isinstance(res, httpx.Response) and res.status_code == 200:
                            data = res.json()
                            author_name = data.get('author', 'Unknown')
                            author_id = data.get('authorId', '')
                            
                            for item in data.get('latestVideos', [])[:5]: # Top 5 per channel
                                # Block Check
                                if item.get('authorId') in blocklist: continue

                                try:
                                    if 'videoId' not in item: continue
                                    
                                    # ... helper to process thumbnail ...
                                    thumb = normalize_thumb(item.get('videoId', ''), item.get('videoThumbnails', [{}])[0].get('url', ''))
                                    
                                    feed_videos.append({
                                        "id": item.get('videoId'),
                                        "title": item.get('title', 'Untitled'),
                                        "uploader": author_name,
                                        "channel_id": author_id,
                                        "thumbnail": thumb,
                                        "view_count": item.get('viewCount', 0),
                                        "published": item.get('published', 0) # For sorting
                                    })
                                except Exception as e:
                                    print(f"Error parsing feed item: {e}")
                                    continue
            
            # PUBLIC SEARCH LOGIC (Only if NOT (all + logged_in))
            search_videos = []
            run_search = True
            
            if category == 'all' and logged_in:
                run_search = False
                
            if run_search:
                url = ""
                if category == 'all':
                    url = f"{INVIDIOUS_API_URL}/api/v1/search?q=台灣+熱門&sort_by=relevance&type=video"
                else:
                    # Generic Search / Custom Nav
                    # Default to treating category as a search query
                    nav_query = category
                    sort_by = "relevance"
                    features = ""
                    
                    if logged_in:
                        user_id = get_user_id(request, creds)
                        nav_items = get_user_nav(user_id)
                        for item in nav_items:
                            if item['id'] == category:
                                nav_query = item['query']
                                # Basic heuristic for sort/features based on query keywords if needed, 
                                # but for now let's just use the query. 
                                # If users want "Live", they should put "Live" in the query or we can add settings later.
                                # For legacy default IDs, we might want to preserve behavior IF they haven't been customized,
                                # but get_user_nav returns the objects with "query" inside them.
                                # The default objects have: query="台灣新聞", query="台灣直播", etc.
                                # So simply using the query from the object is correct.
                                break

                    # Construct URL
                    # Note: We might want to handle 'live' feature if query contains '直播' or 'live', 
                    # but Invidious search usually handles 'features=live' separately.
                    # For now, simplistic approach:
                    url = f"{INVIDIOUS_API_URL}/api/v1/search?q={nav_query}&type=video"
                    
                    # Special handling for legacy defaults if they are still using original queries?
                    # No, the goal is FULL customization.
                    # However, "Live" usually needs `&features=live` to be strictly live.
                    # If the user sets query "game live", they might expect live streams.
                    # Adding a simple check:
                    if "直播" in nav_query or "live" in nav_query.lower():
                         url += "&features=live"
                    if "新聞" in nav_query or "news" in nav_query.lower():
                         url += "&sort_by=upload_date" # News usually necessitates recency
            
                if pageToken:
                    url += f"&page={pageToken}"
                
                resp = await client.get(url)
                data = resp.json()
                
                if isinstance(data, list):
                    for item in data:
                         if 'videoId' not in item or 'title' not in item: continue
                         
                         # Block Check
                         if item.get('authorId') in blocklist: continue

                         # ... same thumb logic ...
                         thumbnails = item.get('videoThumbnails', [])
                         thumb = normalize_thumb(item.get('videoId', ''), thumbnails[0].get('url', '') if thumbnails else '')

                         search_videos.append({
                            "id": item['videoId'],
                            "title": item['title'],
                            "uploader": item.get('author', 'Unknown'),
                            "channel_id": item.get('authorId', ''),
                            "thumbnail": thumb,
                            "view_count": item.get('viewCount', 0)
                        })

            # MERGE & SHUFFLE
            # If we have feed videos, show them first, mixed with some popular ones
            final_list = feed_videos + search_videos
            # Remove duplicates
            seen = set()
            unique_list = []
            for v in final_list:
                if v['id'] not in seen:
                    unique_list.append(v)
                    seen.add(v['id'])
            
            # If we have personalized content, maybe shuffle a bit or just return
            return {"videos": unique_list, "nextPageToken": str(int(pageToken)+1) if pageToken and pageToken.isdigit() else "2"}
            
        except Exception as e:
            print(f"Error proxying invidious: {e}")
            return {"videos": [], "error": str(e)}

@app.get("/search")
async def search_page(request: Request, q: str):
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    
    blocklist = {}
    if logged_in:
        user_id = get_user_id(request, creds)
        blocklist = get_user_blocklist(user_id)

    videos = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{INVIDIOUS_API_URL}/api/v1/search",
                params={"q": q, "type": "video", "sort_by": "relevance"}
            )
            data = resp.json()
            print(f"[search] q='{q}' status={resp.status_code} items={len(data) if isinstance(data, list) else 'n/a'}")
            for item in data:
                if 'videoId' not in item or 'title' not in item:
                    continue
                
                # Block Check
                if item.get('authorId') in blocklist: continue

                thumbnails = item.get('videoThumbnails', [])
                thumb = normalize_thumb(item.get('videoId', ''), thumbnails[0].get('url', '') if thumbnails else '')

                videos.append({
                    "id": item['videoId'],
                    "title": item['title'],
                    "uploader": item.get('author', 'Unknown'),
                    "channel_id": item.get('authorId', ''),
                    "thumbnail": thumb,
                    "view_count": item.get('viewCount', 0)
                })
        except Exception as e:
            print(f"search error: {e}")
            videos = []

    return templates.TemplateResponse("results.html", {"request": request, "query": q, "videos": videos, "logged_in": logged_in})


@app.get("/channel")
async def channel_page(request: Request, c: str, name: str = ""):
    """
    Channel landing page to show latest videos.
    Query params:
      - c: channelId (Invidious authorId/YouTube channel ID)
      - name: optional channel title for display
    """
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    return templates.TemplateResponse("channel.html", {"request": request, "channel_id": c, "channel_name": name, "logged_in": logged_in})

@app.get("/channel/")
async def channel_page_slash(request: Request, c: str = "", name: str = ""):
    # trailing slash fallback
    if not c:
        raise HTTPException(status_code=400, detail="channelId is required")
    return await channel_page(request, c, name)

# --- Playlist Routes ---

@app.get("/playlist")
async def playlist_page(request: Request, list: str):
    """
    Playlist page.
    """
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    return templates.TemplateResponse("playlist.html", {"request": request, "playlist_id": list, "logged_in": logged_in})

@app.get("/api/playlist/{playlistId}")
async def get_playlist_details(playlistId: str):
    """
    Fetch full playlist details from Invidious.
    """
    async with httpx.AsyncClient() as client:
        try:
            url = f"{INVIDIOUS_API_URL}/api/v1/playlists/{playlistId}"
            resp = await client.get(url)
            data = resp.json()
            
            videos = []
            for item in data.get('videos', []):
                 thumb = normalize_thumb(item.get('videoId', ''), item.get('videoThumbnails', [{}])[0].get('url', ''))
                 videos.append({
                     "id": item.get('videoId'),
                     "title": item.get('title'),
                     "uploader": item.get('author'),
                     "channel_id": data.get('authorId'), # Usually playlist author
                     "thumbnail": thumb,
                     "view_count": item.get('index', 0) # Index in playlist
                 })
            
            info = {
                "title": data.get('title'),
                "author": data.get('author'),
                "authorId": data.get('authorId'),
                "description": data.get('description', ''),
                "viewCount": data.get('viewCount', 0),
                "updated": data.get('updated', ''),
                "videoCount": data.get('videoCount', 0),
                "thumbnail": data.get('playlistThumbnail'),
                "videos": videos
            }
            return info
        except Exception as e:
            print(f"playlist_details error: {e}")
            return {"error": str(e)}


@app.get("/api/channel/{channelId}")
async def get_channel_details(channelId: str):
    """
    Fetch full channel details from Invidious.
    """
    async with httpx.AsyncClient() as client:
        try:
            url = f"{INVIDIOUS_API_URL}/api/v1/channels/{channelId}"
            resp = await client.get(url)
            data = resp.json()
            
            # Process videos
            videos = []
            for item in data.get('latestVideos', []):
                thumb = normalize_thumb(item.get('videoId', ''), item.get('videoThumbnails', [{}])[0].get('url', ''))
                videos.append({
                    "id": item.get('videoId'),
                    "title": item.get('title', ''),
                    "uploader": data.get('author', ''),
                    "channel_id": channelId,
                    "thumbnail": thumb,
                    "view_count": item.get('viewCount', 0),
                    "published": item.get('publishedText', '')
                })

            # Extract Profile Info
            banner = None
            if data.get('authorBanners'):
                banner = data['authorBanners'][0]['url']
            
            avatar = ""
            if data.get('authorThumbnails'):
                avatar = data['authorThumbnails'][-1]['url'] # High res

            info = {
                "title": data.get('author'),
                "id": data.get('authorId'),
                "description": data.get('description'),
                "subCount": data.get('subCount', 0),
                "totalViews": data.get('totalViews', 0),
                "banner": banner,
                "avatar": avatar,
                "videos": videos
            }
            return info
        except Exception as e:
            print(f"channel_details error: {e}")
            return {"error": str(e)}

@app.get("/api/channel/{channelId}/playlists")
async def get_channel_playlists(channelId: str):
    """
    Fetch playlists of a channel.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Invidious often paginates, but /playlists usually returns first batch
            url = f"{INVIDIOUS_API_URL}/api/v1/channels/{channelId}/playlists"
            resp = await client.get(url)
            data = resp.json()
            
            playlists = []
            if isinstance(data, dict) and data.get('playlists'):
                 items = data['playlists']
            elif isinstance(data, list):
                 items = data
            else:
                 items = []
                 
            for item in items:
                # Basic normalization
                playlists.append({
                    "id": item.get('playlistId'),
                    "title": item.get('title'),
                    "thumbnail": item.get('playlistThumbnail') or '',
                    "count": item.get('videoCount', 0)
                })
            return {"playlists": playlists}
        except Exception as e:
            print(f"channel_playlists error: {e}")
            return {"playlists": [], "error": str(e)}

@app.get("/api/channel_videos")
async def channel_videos(channelId: str):
    # Backward compatibility or valid partial fetch
    return await get_channel_details(channelId)

@app.get("/api/get_stream")
async def get_stream_proxy(request: Request, v: str):
    """
    Fetch video details from Invidious and return the best stream URL.
    """
    creds = get_creds(request)
    blocklist = {}
    if creds:
        user_id = get_user_id(request, creds)
        blocklist = get_user_blocklist(user_id)

    async with httpx.AsyncClient() as client:
        try:
            url = f"{INVIDIOUS_API_URL}/api/v1/videos/{v}"
            resp = await client.get(url)
            data = resp.json()
            
            # Find adaptiveFormats or formatStreams
            # We prefer mp4 and 720p/360p for legacy support
            streams = data.get('formatStreams', [])
            best_stream = None
            
            # Try formatStreams (combined)
            for s in streams:
                if s.get('container') == 'mp4':
                    best_stream = s.get('url')
                    break 
            
            # If no combined streams, try adaptive (will only be video or audio, but better than nothing)
            if not best_stream:
                adaptive = data.get('adaptiveFormats', [])
                for a in adaptive:
                    if a.get('container') == 'mp4' and a.get('type', '').startswith('video'):
                        best_stream = a.get('url')
                        break
            
            # Metadata for UI
            info = {
                "title": data.get('title'),
                "uploader": data.get('author'),
                "channel_id": data.get('authorId'),
                "description": data.get('description', '')[:200] + "...",
                "view_count": data.get('viewCount')
            }

            # Related Videos
            related = []
            
            for item in data.get('recommendedVideos', []):
                if 'videoId' not in item or 'title' not in item: continue
                
                # Block Check
                if item.get('authorId') in blocklist: continue
                
                thumbnails = item.get('videoThumbnails', [])
                thumb = normalize_thumb(item.get('videoId', ''), thumbnails[0].get('url', '') if thumbnails else '')
                
                related.append({
                    "id": item['videoId'],
                    "title": item['title'],
                    "uploader": item.get('author', 'Unknown'),
                    "channel_id": item.get('authorId', ''),
                    "thumbnail": thumb,
                    "view_count": item.get('viewCount', 0)
                })
            
            if not best_stream:
                 return {"error": "No suitable stream found"}
            
            # Proxy the stream via our own server to bypass IP/Domain restrictions
            import urllib.parse
            encoded_url = urllib.parse.quote(best_stream)
            proxied_url = f"/api/stream_proxy?url={encoded_url}"

            return {
                "stream_url": proxied_url,
                "info": info,
                "mime_type": "video/mp4",
                "related_videos": related
            }

        except Exception as e:
            return {"error": str(e)}

@app.get("/api/stream_proxy")
async def stream_proxy(url: str, request: Request):
    """
    Proxy video stream to bypass CORS and IP restrictions.
    """
    import sys
    print(f"[Proxy] Request for: {url[:80]}...", flush=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.youtube.com/",
    }
    
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
        print(f"[Proxy] Range: {range_header}", flush=True)

    async def generate():
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        try:
            print(f"[Proxy] Connecting...", flush=True)
            async with client.stream("GET", url, headers=headers) as resp:
                print(f"[Proxy] Status: {resp.status_code}", flush=True)
                
                if resp.status_code >= 400:
                    print(f"[Proxy] Error: {resp.status_code}", flush=True)
                    yield b""
                    return
                
                chunk_num = 0
                async for chunk in resp.aiter_bytes(chunk_size=64*1024):
                    chunk_num += 1
                    if chunk_num == 1:
                        print(f"[Proxy] Streaming started, first chunk: {len(chunk)} bytes", flush=True)
                    yield chunk
                    
                print(f"[Proxy] Complete: {chunk_num} chunks", flush=True)
        except Exception as e:
            print(f"[Proxy] Error: {e}", flush=True)
            yield b""
        finally:
            await client.aclose()
    
    # CORS headers to allow browser access
    response_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Range",
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
    }
    
    print(f"[Proxy] Returning StreamingResponse", flush=True)
    return StreamingResponse(
        generate(),
        media_type="video/mp4",
        headers=response_headers
    )

@app.get("/manage/subscriptions", response_class=HTMLResponse)
async def manage_subscriptions(request: Request):
    creds = get_creds(request)
    if not creds or not creds.valid:
        return RedirectResponse("/login")
    
    logged_in = True
    subs = fetch_subscriptions_internal(creds, max_results=200) # Fetch more for manager
    
    items = []
    if subs:
        items = subs # Already in correct format: {title, channelId, thumbnail}
        
    return templates.TemplateResponse("manager.html", {
        "request": request, 
        "logged_in": logged_in,
        "title": "訂閱管理",
        "view_type": "subscriptions",
        "items": items
    })

@app.get("/manage/blocked", response_class=HTMLResponse)
async def manage_blocked(request: Request):
    creds = get_creds(request)
    if not creds or not creds.valid:
        return RedirectResponse("/login")
    
    logged_in = True
    user_id = get_user_id(request, creds)
    blocklist = get_user_blocklist(user_id) # {id: name}
    
    items = []
    for cid, name in blocklist.items():
        items.append({
            "title": name,
            "channelId": cid,
            "thumbnail": "" # No thumb stored for blocks
        })
        
    return templates.TemplateResponse("manager.html", {
        "request": request, 
        "logged_in": logged_in,
        "title": "封鎖管理",
        "view_type": "blocked",
        "items": items
    })

# --- Navigation Management ---

def get_user_nav(user_id):
    path = os.path.join(DATA_DIR, 'users', f"{user_id}_nav.json")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return []
    
    # Default Nav
    return [
        {"id": "news", "title": "新聞", "query": "台灣新聞", "is_fixed": False},
        {"id": "live", "title": "直播", "query": "台灣直播", "is_fixed": False},
        {"id": "podcast", "title": "Podcast", "query": "Podcast", "is_fixed": False}
    ]

def save_user_nav(user_id, nav_items):
    path = os.path.join(DATA_DIR, 'users', f"{user_id}_nav.json")
    with open(path, 'w') as f:
        json.dump(nav_items, f)

class NavUpdate(pydantic.BaseModel):
    items: list

@app.get("/api/nav")
def get_nav(request: Request):
    creds = get_creds(request)
    if not creds: return []
    user_id = get_user_id(request, creds)
    return get_user_nav(user_id)

@app.post("/api/nav")
async def update_nav(request: Request, body: NavUpdate):
    creds = get_creds(request)
    if not creds: return {"error": "Not logged in"}
    user_id = get_user_id(request, creds)
    save_user_nav(user_id, body.items)
    return {"status": "success"}

@app.get("/manage/nav", response_class=HTMLResponse)
async def manage_nav(request: Request):
    creds = get_creds(request)
    if not creds or not creds.valid:
        return RedirectResponse("/login")
    
    logged_in = True
    user_id = get_user_id(request, creds)
    items = get_user_nav(user_id)
    
    return templates.TemplateResponse("nav_manager.html", {
        "request": request,
        "logged_in": logged_in,
        "items": items
    })

# --- Download API ---

class DownloadRequest(pydantic.BaseModel):
    id: str
    title: str
    format: str = "mp3" # mp3 or mp4
    type: str = "video" # video or playlist
    is_cache: bool = False

@app.post("/api/download")
async def start_download(job: DownloadRequest):
    # For now, we only support single video downloads in MVP
    job_id = queue_manager.add_job(job.id, job.title, job.format, job.type, job.is_cache)
    return {"status": "queued", "job_id": job_id}

@app.get("/api/downloads")
async def get_downloads():
    jobs = queue_manager.get_jobs()
    # Filter out cache jobs from public list
    return [j for j in jobs if not j.get('is_cache', False)]

@app.get("/api/download/status/{job_id}")
async def get_download_status(job_id: str):
    """Get status of a specific download job"""
    jobs = queue_manager.get_jobs()
    job = next((j for j in jobs if j['job_id'] == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@app.delete("/api/downloads/{job_id}")
async def cancel_download(job_id: str):
    queue_manager.cancel_job(job_id)
    queue_manager.clear_job(job_id)
    return {"status": "deleted"}

@app.get("/api/download_file/{job_id}")
async def download_file(job_id: str):
    # Find job
    jobs = queue_manager.get_jobs()
    job = next((j for j in jobs if j['job_id'] == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Check for file path (prefer 'file_path', fallback to 'filename')
    file_path = job.get('file_path') or job.get('filename')

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File deleted from server")

    # Determine friendly filename for user
    # Use title but sanitize it slightly to be safe
    raw_title = job.get('title', 'download')
    # Keep alphanumeric, spaces, dashes, underscores, and dots (except leading dots)
    safe_chars = "".join([c for c in raw_title if c.isalnum() or c in (' ', '-', '_', '.', '(', ')', '[', ']')])
    safe_title = safe_chars.strip() or "download"
    
    ext = os.path.splitext(file_path)[1]
    if not ext:
        ext = '.mp4' # fallback
        
    friendly_name = f"{safe_title}{ext}"
    
    return FileResponse(
        path=file_path, 
        filename=friendly_name, 
        media_type='application/octet-stream'
    )

@app.get("/downloads", response_class=HTMLResponse)
async def downloads_page(request: Request):
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    return templates.TemplateResponse("downloads.html", {"request": request, "logged_in": logged_in})
