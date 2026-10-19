#!/usr/bin/env bash
# ⚡ vplay Web Dashboard Server Control Manager (Android/Termux, Linux, macOS)
# Usage: ./scripts/server.sh [start|stop|restart|status]

set -u
CMD="${1:-status}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_PATH="$REPO_ROOT/scripts/web_server.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"

is_termux() {
    command -v termux-usb >/dev/null 2>&1
}

get_termux_dev() {
    termux-usb -l | jq -r '.[0]' 2>/dev/null
}

start_server() {
    pkill -f "$SCRIPT_PATH" 2>/dev/null || true
    if is_termux; then
        DEV="$(get_termux_dev)"
        if [ -z "$DEV" ] || [ "$DEV" = "null" ]; then
            echo "❌ No USB OTG device detected."
            echo "   Please connect ESP32 via USB OTG cable and try again."
            return 1
        fi
        echo "🚀 Starting vplay Web Control Dashboard on $DEV (Termux USB OTG)..."
        termux-usb -E -e "$SCRIPT_PATH" "$DEV" &
    else
        echo "🚀 Starting vplay Web Control Dashboard..."
        "$PYTHON_BIN" "$SCRIPT_PATH" &
    fi
    sleep 2
    if pgrep -f "$SCRIPT_PATH" >/dev/null 2>&1; then
        echo "✅ Web Server is LIVE at http://localhost:8080"
    else
        echo "⚠️ Failed to start server. Check output or USB permissions."
        return 1
    fi
}

stop_server() {
    echo "🛑 Stopping vplay Web Control Dashboard..."
    pkill -f "$SCRIPT_PATH" 2>/dev/null || true
    sleep 1
    echo "✅ Server stopped."
}

restart_server() {
    stop_server
    start_server
}

status_server() {
    if pgrep -f "$SCRIPT_PATH" >/dev/null 2>&1; then
        PID="$(pgrep -f "$SCRIPT_PATH" | head -n 1)"
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
