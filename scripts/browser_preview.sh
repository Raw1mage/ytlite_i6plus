# Chrome Preview Controller
# Usage: ./browser_preview.sh [start|stop|logs|status]

USER_DATA_DIR="$HOME/.chrome_dev_profile"
LOG_FILE="$(dirname "$0")/../logs/chrome_preview.log"
PORT=9222

function get_pid() {
    # Find process ID of google-chrome running with our specific port
    pgrep -f "remote-debugging-port=$PORT"
}

function start() {
    local pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo "Chrome is already running (PID: $pid)."
        return
    fi

    # Create directory if needed
    mkdir -p "$USER_DATA_DIR"

    echo "Starting Google Chrome on port $PORT..."
    echo "Logs: $LOG_FILE"
    
    # Launch in background, redirect output to log file
    nohup /usr/bin/google-chrome \
      --remote-debugging-port=$PORT \
      --remote-allow-origins=* \
      --user-data-dir="$USER_DATA_DIR" \
      --no-first-run \
      --no-default-browser-check \
      "https://www.google.com" \
      "$@" >> "$LOG_FILE" 2>&1 &

    sleep 1
    local new_pid=$(get_pid)
    if [ -n "$new_pid" ]; then
        echo "Chrome started successfully (PID: $new_pid)."
    else
        echo "Failed to start Chrome. Check logs."
    fi
}

function stop() {
    local pids=$(get_pid)
    if [ -z "$pids" ]; then
        echo "Chrome is not running."
        return
    fi

    echo "Stopping Chrome (PIDs: $pids)..."
    # Convert newlines to spaces and kill
    echo "$pids" | xargs kill
    
    # Wait for it to exit
    for i in {1..5}; do
        if [ -z "$(get_pid)" ]; then
            echo "Stopped."
            return
        fi
        sleep 0.5
    done
    
    # Force kill if needed
    local rem_pids=$(get_pid)
    if [ -n "$rem_pids" ]; then
        echo "Force killing remaining..."
        echo "$rem_pids" | xargs kill -9
    fi
}

function logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "No log file found at $LOG_FILE"
        return
    fi
    echo "Tailing logs (Ctrl+C to exit)..."
    tail -f "$LOG_FILE"
}

function status() {
    local pid=$(get_pid)
    if [ -n "$pid" ]; then
        echo "Status: Running (PID: $pid)"
        echo "Port: $PORT"
        echo "Profile: $USER_DATA_DIR"
    else
        echo "Status: Stopped"
    fi
}

# Main Dispatcher
case "$1" in
    start)
        shift
        start "$@"
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|logs|status}"
        exit 1
        ;;
esac
