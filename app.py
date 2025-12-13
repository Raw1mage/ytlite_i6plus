from flask import Flask, render_template, request, redirect, url_for
import subprocess
import json
import shutil
import sys

app = Flask(__name__)

# Locate yt-dlp
# Priority: 1. sys.executable path (if installed via pip module) 2. shutil.which 3. Hardcoded path
YTDLP_CMD = "yt-dlp" 
if shutil.which("yt-dlp"):
    YTDLP_CMD = shutil.which("yt-dlp")
else:
    # Fallback to common locations or module execution
    YTDLP_CMD = "/usr/local/bin/yt-dlp"

print(f"Using yt-dlp command: {YTDLP_CMD}")

def get_yt_stream(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        # Fetch best MP4 compatible with iOS
        cmd = [
            YTDLP_CMD, 
            "-g", 
            "-f", "best[ext=mp4]/best", 
            video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if result.returncode != 0:
            print(f"Error getting stream: {result.stderr}")
            return None, None
            
        stream_url = result.stdout.strip()
        
        # Fetch metadata
        cmd_info = [
            YTDLP_CMD, 
            "--dump-json", 
            "--skip-download", 
            video_url
        ]
        result_info = subprocess.run(cmd_info, capture_output=True, text=True, timeout=25)
        info = json.loads(result_info.stdout)
        
        return stream_url, info
    except Exception as e:
        print(f"Exception in get_yt_stream: {e}")
        return None, None

def search_yt(query):
    try:
        cmd = [
            YTDLP_CMD,
            f"ytsearch10:{query}",
            "--dump-json",
            "--default-search", "ytsearch",
            "--no-playlist",
            "--skip-download",
            "--flat-playlist" 
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        results = []
        for line in result.stdout.splitlines():
            if line:
                try:
                    results.append(json.loads(line))
                except:
                    pass
        return results
    except Exception as e:
        print(f"Search Exception: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))
    results = search_yt(query)
    return render_template('results.html', results=results, query=query)

@app.route('/watch')
def watch():
    video_id = request.args.get('v')
    if not video_id:
        return redirect(url_for('index'))
    
    stream_url, info = get_yt_stream(video_id)
    if not stream_url:
        return "Error fetching video stream. Check server logs."
        
    return render_template('watch.html', stream_url=stream_url, info=info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
