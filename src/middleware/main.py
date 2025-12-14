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

TOKEN_PATH = os.path.join(DATA_DIR, 'token.json')
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_creds():
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(GoogleRequest())
                with open(TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
            return creds
        except Exception as e:
            print(f"Auth Error: {e}")
            return None
    return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, response: Response):
    # Force no-cache to prevent browser caching issues
    creds = get_creds()
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
        include_granted_scopes='true')
    
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
    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())
        
    return RedirectResponse("/")

@app.get("/logout")
async def logout(request: Request):
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    request.session.clear()
    return RedirectResponse("/")

from googleapiclient.discovery import build

@app.get("/api/subscriptions")
async def get_subscriptions():
    creds = get_creds()
    if not creds or not creds.valid:
        return {"error": "Not logged in"}
    
    try:
        service = build('youtube', 'v3', credentials=creds)
        
        # Max 50 subscriptions to start
        response = service.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50,
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
        return {"error": str(e)}


@app.get("/api/videos")
async def get_videos(category: str = "all", pageToken: str = ""):
    """
    Proxy request to Invidious API.
    Category Mapping:
    - all -> Invidious Trending or Popular
    - news -> Search "News" or specific channel list?
    """
    async with httpx.AsyncClient() as client:
        try:
            # Map YT Lite categories to Invidious endpoints
            if category == 'all':
                # Use Trending for 'High Performance' default feed
                # endpoint: /api/v1/trending?region=TW
                url = f"{INVIDIOUS_API_URL}/api/v1/trending?region=TW"
            else:
                # Fallback to search for other categories
                url = f"{INVIDIOUS_API_URL}/api/v1/search?q={category}&type=video"
            
            resp = await client.get(url)
            data = resp.json()
            
            # Transform Invidious Data to YT Lite Format
            # Invidious returns: [{videoId:..., title:..., author:..., videoThumbnails:[...]}]
            # YT Lite expects: [{id:..., title:..., uploader:..., thumbnail:...}]
            
            transformed = []
            for item in data:
                # Safety check for minimal fields
                if 'videoId' not in item or 'title' not in item: continue
                
                # Pick best thumbnail (usually high quality is available)
                thumb = item.get('videoThumbnails', [{}])[0].get('url', '')
                if not thumb and 'id' in item: # fallback
                     thumb = f"https://i.ytimg.com/vi/{item['videoId']}/hqdefault.jpg"

                transformed.append({
                    "id": item['videoId'],
                    "title": item['title'],
                    "uploader": item.get('author', 'Unknown'),
                    "thumbnail": thumb,
                    "view_count": item.get('viewCount', 0)
                })
            
            return {"videos": transformed, "nextPageToken": ""}
            
        except Exception as e:
            print(f"Error proxying invidious: {e}")
            return {"videos": [], "error": str(e)}

@app.get("/search")
async def search_page(request: Request, q: str):
    return templates.TemplateResponse("results.html", {"request": request, "query": q, "videos": []})

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
            
            if not best_stream:
                 return {"error": "No suitable stream found"}
            
            return {
                "stream_url": best_stream,
                "info": info,
                "mime_type": "video/mp4" # Assumption
            }

        except Exception as e:
            return {"error": str(e)}

