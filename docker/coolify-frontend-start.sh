#!/bin/bash
set -euo pipefail

if [[ ! ${CRM_BACKEND_URL:-} =~ ^http://[a-zA-Z0-9][a-zA-Z0-9-]{0,62}:4178$ ]]; then
    echo 'CRM_BACKEND_URL must point to the private Docker hostname on port 4178.' >&2
    exit 1
fi

mkdir -p /tmp/nginx/{client,proxy,fastcgi,uwsgi,scgi}
envsubst '${CRM_BACKEND_URL}' < /etc/nginx/frontend.conf.template > /tmp/nginx/frontend.conf
exec nginx -c /tmp/nginx/frontend.conf -g 'daemon off;'
