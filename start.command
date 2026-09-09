#!/bin/bash
# lilchat launcher — double-click to run. Ctrl+C in this window stops everything.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PORT_LILCHAT=8889
PORT_SEARXNG=8888
PORT_LLM=8086

SEARXNG_PID=""
LILCHAT_PID=""

cleanup() {
    echo ""
    echo "Stopping lilchat..."
    [ -n "$LILCHAT_PID" ] && kill "$LILCHAT_PID" 2>/dev/null
    [ -n "$SEARXNG_PID" ] && kill "$SEARXNG_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

port_open() { curl -s -o /dev/null --max-time 1 "http://localhost:$1/" ; }

# ── Python ────────────────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 not found."
    echo "Install it with:  brew install python3"
    echo "or download from: https://www.python.org/downloads/"
    read -p "Press Enter to close..."; exit 1
fi

# ── LLM (must already be running — we only check) ─────────────────────────
if port_open $PORT_LLM; then
    echo "✓ LLM server found on port $PORT_LLM"
else
    echo "! No LLM server on port $PORT_LLM — start your model (e.g. qwen384) first."
    echo "  lilchat will still open, but chat won't work until the model is up."
fi

# ── SearXNG (optional: reuse if running, else try to start, else skip) ────
if port_open $PORT_SEARXNG; then
    echo "✓ SearXNG already running on port $PORT_SEARXNG"
elif command -v searxng >/dev/null 2>&1; then
    echo "Starting SearXNG..."
    searxng >/dev/null 2>&1 &
    SEARXNG_PID=$!
    for i in $(seq 1 20); do
        port_open $PORT_SEARXNG && break
        sleep 1
    done
    if port_open $PORT_SEARXNG; then
        echo "✓ SearXNG ready"
    else
        echo "! SearXNG did not come up — web search will be unavailable."
    fi
else
    echo "! SearXNG not installed — web search disabled (chat + URL fetch still work)."
fi

# ── lilchat ───────────────────────────────────────────────────────────────
if port_open $PORT_LILCHAT; then
    echo "! Something is already on port $PORT_LILCHAT. Close it and re-run."
    read -p "Press Enter to close..."; exit 1
fi

echo "Starting lilchat..."
python3 "$DIR/proxy.py" &
LILCHAT_PID=$!
for i in $(seq 1 10); do
    port_open $PORT_LILCHAT && break
    sleep 0.5
done

open "http://localhost:$PORT_LILCHAT/"

echo ""
echo "============================================"
echo "  lilchat is running"
echo "  Browser : http://localhost:$PORT_LILCHAT/"
echo "  Stop    : Ctrl+C in this window"
echo "============================================"
wait
