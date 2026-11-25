# syntax=docker/dockerfile:1
FROM node:24.20.0-bookworm-slim@sha256:ba849c60be29959425b8734d57b8b4b7d56f98edd9504c9af091d5281095a71e AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/tsconfig.json frontend/vite.workspace.config.ts frontend/workspace.html ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN ./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/vite build --config vite.workspace.config.ts
FROM crm-cbn-workspace:p8es-r7@sha256:dda6fdc531e30300664a8b189ac996f087cf6d17bebee1afe12fe811e1a980f6
COPY backend/app ./app
COPY backend/tools ./tools
COPY backend/migrations ./migrations
COPY --from=frontend /build/frontend/dist-workspace /app/institution-frontend
COPY docker/nginx.ads.conf /etc/nginx/general.conf
EXPOSE 4178
