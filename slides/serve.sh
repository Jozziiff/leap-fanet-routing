#!/usr/bin/env bash
# Serve the deck at http://127.0.0.1:8766/ (stop with Ctrl+C). Optional argument: another port.
# A local server is needed because the browser cannot load the demo recording from file:// pages.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8766}"
echo "Deck: http://127.0.0.1:$PORT/   presenter view: press P in the deck   stop: Ctrl+C"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
