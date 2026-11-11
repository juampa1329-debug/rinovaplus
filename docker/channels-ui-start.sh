#!/bin/bash
set -euo pipefail
mkdir -p /tmp/nginx/{client,proxy,fastcgi,uwsgi,scgi}
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log &
backend_pid=$!
nginx -c /etc/nginx/channels-ui.conf -g 'daemon off;' &
proxy_pid=$!
trap 'kill "$backend_pid" "$proxy_pid" 2>/dev/null || true; wait || true' EXIT INT TERM
wait -n "$backend_pid" "$proxy_pid"
