#!/bin/bash
cd /var/mobile/Documents/yt_lite
export FLASK_APP=app.py
export FLASK_ENV=development
# Kill existing instance if any
pkill -f "python3 app.py"
echo "Starting YT Lite Server..."
nohup python3 app.py > server.log 2>&1 &
echo "Server started with PID \$!"
