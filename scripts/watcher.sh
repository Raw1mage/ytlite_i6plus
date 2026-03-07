#!/bin/bash

# Watch for the signal file created by the Docker container
SIGNAL_FILE="/home/pkcs12/projects/ytlite/webbox/src/middleware/OPEN_DOWNLOADS.signal"

echo "Starting Download Folder Watcher..."
echo "Watching: $SIGNAL_FILE"

while true; do
    if [ -f "$SIGNAL_FILE" ]; then
        # Read path from file
        TARGET_PATH=$(cat "$SIGNAL_FILE")
        
        echo "Signal received. Target: $TARGET_PATH"
        
        # Remove signal first
        rm "$SIGNAL_FILE"
        
        if [ "$TARGET_PATH" = "EXPLORER" ]; then
            # Open generic My Computer using cmd /c start for robustness
            cmd.exe /c start explorer < /dev/null
        elif [[ "$TARGET_PATH" == *":\\"* ]]; then
             # It's already a Windows Path (e.g. E:\Foo)
             cmd.exe /c start explorer "$TARGET_PATH" < /dev/null
        elif [[ "$TARGET_PATH" == "/"* ]]; then
             # It's a Linux/WSL path
             if [[ "$TARGET_PATH" == *"/app/data/downloads"* ]]; then
                 # Remap Docker internal path to Host path if known
                 HOST_PATH="/opt/ytlite_v3/user_db/downloads"
                 WIN_PATH=$(wslpath -w "$HOST_PATH")
                 cmd.exe /c start explorer "$WIN_PATH" < /dev/null
             else
                 # Try converting generic linux path
                 WIN_PATH=$(wslpath -w "$TARGET_PATH")
                 cmd.exe /c start explorer "$WIN_PATH" < /dev/null
             fi
        else
             # Fallback
             cmd.exe /c start explorer < /dev/null
        fi
    fi
    sleep 1
done
