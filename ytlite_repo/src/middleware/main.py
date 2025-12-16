from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
import os
import json
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

import uuid
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
                creds.refresh(GoogleRequest())
                # Update session (file) with refreshed token
                save_creds_to_session(request, creds)
                
            return creds
        except Exception as e:
            print(f"Auth Error: {e}")
            return None
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

def fetch_subscriptions_internal(creds, max_results=50):
    try:
        service = build('youtube', 'v3', credentials=creds)
        response = service.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=max_results,
            order="alphabetical"
        ).execute()
        
        subs = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            subs.append({
                "channelId": snippet["resourceId"]["channelId"],
                "title": snippet["title"],
                "thumbnail": snippet["thumbnails"]["default"]["url"]
            })
        return subs
    except Exception as e:
        print(f"Sub Error: {e}")
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
    except Exception as e:
        print(f"Sub Action Error: {e}")
        return {"error": str(e)}

@app.get("/api/videos")
async def get_videos(request: Request, category: str = "all", pageToken: str = ""):
    """
    Proxy request to Invidious API.
    """
    creds = get_creds(request)
    logged_in = (creds is not None and creds.valid)
    
    async with httpx.AsyncClient() as client:
        try:
            # PERSONALIZED FEED LOGIC
            feed_videos = []
            if category == 'all' and logged_in and not pageToken:
                # 1. Get Subscriptions
                subs = fetch_subscriptions_internal(creds, max_results=50)
                if subs:
                    # 2. Pick Random 3-5 Channels
                    targets = random.sample(subs, k=min(len(subs), 5))
                    
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
                                # ... helper to process thumbnail ...
                                thumb = normalize_thumb(item.get('videoId', ''), item.get('videoThumbnails', [{}])[0].get('url', ''))
                                
                                feed_videos.append({
                                    "id": item['videoId'],
                                    "title": item['title'],
                                    "uploader": author_name,
                                    "channel_id": author_id,
                                    "thumbnail": thumb,
                                    "view_count": item.get('viewCount', 0),
                                    "published": item.get('published', 0) # For sorting
                                })

            # EXISTING SEARCH LOGIC
            if category == 'all':
                url = f"{INVIDIOUS_API_URL}/api/v1/search?q=台灣+熱門&sort_by=relevance&type=video"
            elif category == 'news':
                url = f"{INVIDIOUS_API_URL}/api/v1/search?q=台灣新聞&sort_by=upload_date&type=video"
            elif category == 'live':
                url = f"{INVIDIOUS_API_URL}/api/v1/search?q=台灣+直播&features=live&type=video"
            elif category == 'podcast':
                url = f"{INVIDIOUS_API_URL}/api/v1/search?q=中文+podcast&type=video"
            else:
                url = f"{INVIDIOUS_API_URL}/api/v1/search?q={category}&type=video"
            
            if pageToken:
                url += f"&page={pageToken}"
            
            resp = await client.get(url)
            data = resp.json()
            
            search_videos = []
            if isinstance(data, list):
                for item in data:
                     if 'videoId' not in item or 'title' not in item: continue
                     
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


@app.get("/api/channel_videos")
async def channel_videos(channelId: str):
    """
    Fetch latest videos of a channel from Invidious.
    """
    async with httpx.AsyncClient() as client:
        try:
            url = f"{INVIDIOUS_API_URL}/api/v1/channels/{channelId}"
            resp = await client.get(url)
            data = resp.json()
            videos = []
            for item in data.get('latestVideos', []):
                thumb = normalize_thumb(item.get('videoId', ''), item.get('videoThumbnails', [{}])[0].get('url', ''))

                videos.append({
                    "id": item.get('videoId'),
                    "title": item.get('title', ''),
                    "uploader": data.get('author', ''),
                    "channel_id": channelId,
                    "thumbnail": thumb,
                    "view_count": item.get('viewCount', 0)
                })
            return {"videos": videos}
        except Exception as e:
            print(f"channel_videos error: {e}")
            return {"videos": [], "error": str(e)}

@app.get("/api/get_stream")
async def get_stream_proxy(v: str):
    """
    Fetch video details from Invidious and return the best stream URL.
    """
    async with httpx.AsyncClient() as client:
        try:
            url = f"{INVIDIOUS_API_URL}/api/v1/videos/{v}"
            resp = await client.get(url)
            data = resp.json()
            
            # Find adaptiveFormats or formatStreams
            # We prefer mp4 and 720p/360p for legacy support
            streams = data.get('formatStreams', [])
            best_stream = None
            
            # Simple Selection Strategy: Best MP4 standard (audio+video)
            # Invidious usually provides 'formatStreams' which are combined.
            for s in streams:
                if s.get('container') == 'mp4':
                    best_stream = s.get('url')
                    # If we find 720p, take it and break? Or try to find exact match?
                    # Let's just take the first MP4 for now (usually sorted by quality)
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
            
            return {
                "stream_url": best_stream,
                "info": info,
                "mime_type": "video/mp4", # Assumption
                "related_videos": related
            }

        except Exception as e:
            return {"error": str(e)}
