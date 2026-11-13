#!/bin/bash
set -euo pipefail
mkdir -p /tmp/nginx/{client,proxy,fastcgi,uwsgi,scgi}
if [[ -z "${CRM_SQL_URL+x}" && -z "${SSL_CERT_FILE+x}" && -r /run/cbn-sql/ca-bundle.pem ]]; then
    export SSL_CERT_FILE=/run/cbn-sql/ca-bundle.pem
fi
python -m app.institutional.coolify_proxy
exec /bin/bash /app/institution-start.sh /tmp/nginx/coolify.conf
