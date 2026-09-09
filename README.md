# lilchat

A minimal chat UI for your local LLM, with optional web search and URL fetch.

## What's in the folder

- `start.command` — double-click this. Starts everything in one Terminal window.
- `proxy.py` — small Python server (serves the UI, relays LLM / search / URL requests)
- `chat.html` — the chat UI
- `README.md` — this file

## First-time setup

1. **Python 3.** Open Terminal and type `python3 --version`. If macOS offers to
   install developer tools, say yes. Otherwise: `brew install python3` or
   https://www.python.org/downloads/

2. **Your LLM server** must be running and expose an OpenAI-compatible
   `/v1/chat/completions` endpoint on port **8086** (that's what `mlx_vlm.server`
   / `mlx_lm.server` do). If yours uses a different port, edit the `LLM = ...`
   line near the top of `proxy.py`.

3. **First launch:** macOS Gatekeeper will block `start.command`.
   Right-click it → **Open** → **Open** again. After that, double-click works.

## Daily use

1. Start your LLM (e.g. `Qwen 3.8`).
2. Double-click `start.command`. A Terminal window opens and the browser
   opens to `http://localhost:8889/`.
3. First time only: click the gear (⚙) and enter the **Model** name your LLM
   expects (for mlx_vlm this is the full model path). Save. It's remembered.

## Features

- **Chat** with your local LLM.
- **Web search** — toggle "Web search" to answer questions using live results.
  Requires a SearXNG instance on port 8888. If you have one and a `searxng`
  command on your PATH, `start.command` starts it for you. If not, search is
  simply disabled — everything else still works.
- **URL fetch** — paste a URL in your message; lilchat reads the page and
  summarizes it. Works with or without SearXNG.
- **History** — the sidebar keeps your chats in the browser. ✕ to delete.
- **Import / Export** — in Settings (⚙) → Chats. Export saves every chat to a
  JSON file you can back up or move to another machine. Import accepts that
  file, or a **Claude.ai data export** (`conversations.json` from
  claude.ai → Settings → Privacy → Export data). Existing chats are kept and
  duplicates are skipped, so re-importing is safe.

## Stopping

`Ctrl+C` in the Terminal window that opened. That stops lilchat (and SearXNG
if lilchat started it). Your LLM keeps running in its own window.

## Using it from another Mac on your network

`proxy.py` listens on all interfaces. From another device open
`http://<this-mac's-IP>:8889/` (find the IP with `ipconfig getifaddr en0`).
The UI auto-detects the host, so nothing needs configuring on the other end.
If macOS asks whether to allow incoming connections for Python, allow it.
