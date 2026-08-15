FROM node:22-alpine AS admin-build
WORKDIR /build/admin
COPY frontend/admin/package*.json ./
RUN npm ci
COPY frontend/admin/ ./
RUN npm run build

FROM node:22-alpine AS web-build
WORKDIR /build/web
COPY frontend/web/package*.json ./
RUN npm ci
COPY frontend/web/ ./
RUN npm run build

FROM caddy:2.10-alpine
COPY infrastructure/Caddyfile /etc/caddy/Caddyfile
COPY --from=admin-build /build/admin/dist /srv/admin
COPY --from=web-build /build/web/dist /srv/web
