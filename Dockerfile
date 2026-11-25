# syntax=docker/dockerfile:1
FROM node:24.20.0-bookworm-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public
# Relative catalog requests contain no credential or environment-specific backend URL.
ENV VITE_CATALOG_API_BASE_URL=""
RUN npm run build

FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CRM_APP_MODE=local_demo \
    CRM_AI_OUTBOUND_ENABLED=false CRM_AI_STATE_DIR=/var/lib/crm-ai
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl nginx unixodbc libgssapi-krb5-2 \
    && curl --fail --silent --show-error --location https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb --output /tmp/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/* /tmp/packages-microsoft-prod.deb \
    && groupadd --gid 10001 crm \
    && useradd --uid 10001 --gid crm --no-create-home --shell /usr/sbin/nologin crm \
    && mkdir -p /var/lib/crm-ai /tmp/nginx \
    && chown crm:crm /var/lib/crm-ai /tmp/nginx
WORKDIR /app/backend
COPY backend/requirements.lock ./requirements.lock
RUN python -m pip install --no-cache-dir --requirement requirements.lock
COPY backend/app ./app
COPY backend/tools/foundation_snapshot.py ./tools/foundation_snapshot.py
COPY backend/migrations/cbn_foundation/release.json backend/migrations/cbn_foundation/expected-shapes.json ./migrations/cbn_foundation/
COPY --from=frontend /build/frontend/dist /app/frontend
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/start.sh /app/start.sh
RUN chmod 0555 /app/start.sh
USER 10001:10001
EXPOSE 4173
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4173/health/live', timeout=3).close()"]
ENTRYPOINT ["/bin/bash", "/app/start.sh"]
