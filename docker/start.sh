#!/bin/bash
set -euo pipefail

backend_pid=""
web_pid=""
frontend_pid=""
cleanup() {
    trap - EXIT TERM INT
    if [[ -n "$web_pid" ]]; then kill -TERM "$web_pid" 2>/dev/null || true; fi
    if [[ -n "$backend_pid" ]]; then kill -TERM "$backend_pid" 2>/dev/null || true; fi
    if [[ -n "$frontend_pid" ]]; then kill -TERM "$frontend_pid" 2>/dev/null || true; fi
    wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT

if [[ -n "${CRM_SQL_CA_FILE:-}" ]]; then
    python - <<'PY'
import os
import ssl
from pathlib import Path

certificate = Path(os.environ["CRM_SQL_CA_FILE"]).read_bytes()
if len(certificate) > 100000 or b"PRIVATE KEY" in certificate:
    raise RuntimeError("Only a bounded public certificate is accepted")
ssl.create_default_context().load_verify_locations(cadata=certificate.decode("ascii"))
system_roots = Path("/etc/ssl/certs/ca-certificates.crt").read_bytes()
bundle = Path("/tmp/crm-ca-bundle.pem")
bundle.write_bytes(system_roots + b"\n" + certificate)
bundle.chmod(0o600)
PY
    export SSL_CERT_FILE=/tmp/crm-ca-bundle.pem
fi

backend_options=(--workers 1)
nginx_options=()
child_pids=()
if [[ "${CRM_LIVE_DEVELOPMENT:-false}" == "true" ]]; then
    backend_options=(--reload --reload-dir /app/backend/app --reload-delay 0.5)
    nginx_options=(-c /etc/nginx/nginx.development.conf)
    (
        cd /app/frontend-source
        exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
    ) &
    frontend_pid=$!
    child_pids+=("$frontend_pid")
fi

python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 "${backend_options[@]}" \
    --no-proxy-headers --no-access-log --timeout-graceful-shutdown 10 &
backend_pid=$!
nginx "${nginx_options[@]}" -g 'daemon off;' &
web_pid=$!
child_pids+=("$backend_pid" "$web_pid")

# A failed child must terminate the container, never leave a half-alive preview.
set +e
wait -n "${child_pids[@]}"
status=$?
set -e
if [[ "$status" -eq 0 ]]; then status=1; fi
exit "$status"
