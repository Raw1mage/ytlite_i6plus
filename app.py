import os
import subprocess
import json
import shutil
import re
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = 'fixed_key_for_sequential_test'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

CLIENT_SECRETS_FILE = '/var/mobile/Documents/yt_lite/client_secret.json'
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

YTDLP_CMD = "yt-dlp"
if shutil.which("yt-dlp"):
    YTDLP_CMD = shutil.which("yt-dlp")
else:
    YTDLP_CMD = "/usr/local/bin/yt-dlp"

def get_credentials():
    token_path = '/var/mobile/Documents/yt_lite/token.json'
    credentials = None
    if os.path.exists(token_path):
        try: credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
        except: credentials = None
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try: credentials.refresh(Request())
            except: credentials = None
    if credentials:
        with open(token_path, 'w') as token:
            token.write(credentials.to_json())
    return credentials

def parse_duration(pt_string):
    if not pt_string: return 0
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(pt_string)
    if not match: return 0
    h, m, s = match.groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)

@app.route('/')
def index():
    credentials = get_credentials()
    return render_template('index.html', logged_in=(credentials is not None))

@app.route('/api/videos')
def api_videos():
    print("DEBUG: Sequential api_videos started")
    credentials = get_credentials()
    if not credentials:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
        
        # 1. Get Subscriptions (Limit to 8 to keep it fast)
        subs_resp = youtube.subscriptions().list(
            part="snippet,contentDetails",
            mine=True,
            maxResults=8, 
            order="relevance"
        ).execute()
        
        potential_videos = []
        
        # 2. Sequential Fetch
        for sub in subs_resp.get('items', []):
            try:
                channel_title = sub['snippet']['title']
                print(f"DEBUG: Fetching channel {channel_title}")
                channel_id = sub['snippet']['resourceId']['channelId']
                uploads_playlist_id = 'UU' + channel_id[2:]
                
                pl_resp = youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=2 # Get 2 latest per channel
                ).execute()
                
                for item in pl_resp.get('items', []):
                    vid_id = item['contentDetails']['videoId']
                    potential_videos.append({
                        "id": vid_id,
                        "title": item['snippet']['title'],
                        "thumbnail": item['snippet']['thumbnails']['medium']['url'],
                        "uploader": item['snippet']['channelTitle'],
                        "publishedAt": item['snippet']['publishedAt']
                    })
            except Exception as e:
                print(f"DEBUG: Error fetching channel: {e}")
                continue
        
        if not potential_videos:
             return jsonify({"videos": [], "nextPageToken": ""})

        # 3. Batch Duration Check
        print(f"DEBUG: Checking duration for {len(potential_videos)} videos")
        video_ids = [v['id'] for v in potential_videos]
        vid_details_resp = youtube.videos().list(
            part="contentDetails",
            id=','.join(video_ids)
        ).execute()
        
        duration_map = {}
        for item in vid_details_resp.get('items', []):
            duration_map[item['id']] = parse_duration(item['contentDetails']['duration'])
            
        final_videos = []
        for v in potential_videos:
            duration = duration_map.get(v['id'], 0)
            if duration > 60:
                final_videos.append(v)
        
        final_videos.sort(key=lambda x: x['publishedAt'], reverse=True)
        
        print(f"DEBUG: Done. Returning {len(final_videos)} videos")
        return jsonify({
            "videos": final_videos,
            "nextPageToken": "" 
        })

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query: return redirect(url_for('index'))
    credentials = get_credentials()
    if credentials:
        try:
            youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
            search_response = youtube.search().list(q=query, part="id,snippet", maxResults=10, type="video").execute()
            results = []
            for item in search_response.get("items", []):
                results.append({"id": item["id"]["videoId"], "title": item["snippet"]["title"], "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"], "uploader": item["snippet"]["channelTitle"]})
            return render_template('results.html', results=results, query=query, logged_in=True)
        except: pass
    cmd = [YTDLP_CMD, f"ytsearch10:{query}", "--dump-json", "--default-search", "ytsearch", "--no-playlist", "--skip-download", "--flat-playlist"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    results = []
    for line in result.stdout.splitlines():
        try:
            data = json.loads(line)
            results.append({"id": data.get("id"), "title": data.get("title"), "thumbnail": data.get("thumbnail"), "uploader": data.get("uploader")})
        except: continue
    return render_template('results.html', results=results, query=query, logged_in=False)

def get_yt_stream(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        cmd = [YTDLP_CMD, "-g", "-f", "best", video_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if result.returncode != 0: return None, None
        stream_url = result.stdout.strip()
        cmd_info = [YTDLP_CMD, "--dump-json", "--skip-download", video_url]
        result_info = subprocess.run(cmd_info, capture_output=True, text=True, timeout=25)
        info = json.loads(result_info.stdout)
        return stream_url, info
    except: return None, None

@app.route('/watch')
def watch():
    video_id = request.args.get('v')
    if not video_id: return redirect(url_for('index'))
    stream_url, info = get_yt_stream(video_id)
    if not stream_url: return "Error fetching stream"
    mime_type = "video/mp4"
    if ".m3u8" in stream_url: mime_type = "application/vnd.apple.mpegurl"
    return render_template('watch.html', stream_url=stream_url, info=info, mime_type=mime_type)

@app.route('/login')
def login():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    with open(os.path.join(app.root_path, 'token.json'), 'w') as token:
        token.write(credentials.to_json())
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    try: os.remove(os.path.join(app.root_path, 'token.json'))
    except: pass
    return redirect(url_for('index'))

@app.route('/install')
def install():
    from flask import send_file
    return send_file('yt-lite.mobileconfig', as_attachment=True, mimetype='application/x-apple-aspen-config')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
