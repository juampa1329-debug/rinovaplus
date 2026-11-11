#!/bin/bash
set -euo pipefail
mkdir -p /tmp/nginx/{client,proxy,fastcgi,uwsgi,scgi}
python -m uvicorn app.institutional.api:application --factory --host 127.0.0.1 --port 8004 --no-access-log --no-proxy-headers &
backend_pid=$!
nginx -c /etc/nginx/general.conf -g 'daemon off;' &
proxy_pid=$!
trap 'kill "$backend_pid" "$proxy_pid" 2>/dev/null || true; wait || true' EXIT INT TERM
wait -n "$backend_pid" "$proxy_pid"
