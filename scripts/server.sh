#!/data/data/com.termux/files/usr/bin/bash
# ⚡ ESP32 Web Dashboard Server Control Manager
# Usage: ./scripts/server.sh [start|stop|restart|status]

CMD=${1:-status}
SCRIPT_PATH="/data/data/com.termux/files/home/trials/vplay/scripts/web_server.py"

get_dev() {
    termux-usb -l | jq -r '.[0]' 2>/dev/null
}

start_server() {
    pkill -f "$SCRIPT_PATH" 2>/dev/null
    DEV=$(get_dev)
    if [ -z "$DEV" ] || [ "$DEV" == "null" ]; then
        echo "❌ No USB OTG device detected."
        echo "   Please connect ESP32 via USB OTG cable and try again."
        return 1
    fi
    echo "🚀 Starting ESP32 Web Control Dashboard on $DEV..."
    termux-usb -E -e "$SCRIPT_PATH" "$DEV" &
    sleep 2
    if pgrep -f "$SCRIPT_PATH" > /dev/null; then
        echo "✅ Web Server is LIVE at http://localhost:8080"
    else
        echo "⚠️ Failed to start server. Please check USB permission prompt."
    fi
}

stop_server() {
    echo "🛑 Stopping ESP32 Web Control Dashboard..."
    pkill -f "$SCRIPT_PATH" 2>/dev/null
    sleep 1
    echo "✅ Server stopped."
}

restart_server() {
    stop_server
    start_server
}

status_server() {
    if pgrep -f "$SCRIPT_PATH" > /dev/null; then
        PID=$(pgrep -f "$SCRIPT_PATH" | head -n 1)
        echo "🟢 Web Server is RUNNING (PID: $PID)"
        echo "   URL: http://localhost:8080"
    else
        echo "🔴 Web Server is STOPPED"
    fi
}

case "$CMD" in
    start)   start_server ;;
    stop)    stop_server ;;
    restart) restart_server ;;
    status)  status_server ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac
