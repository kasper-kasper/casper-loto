FROM node:22-alpine AS admin-build
WORKDIR /build/admin
COPY frontend/admin/package*.json ./
RUN npm ci
COPY frontend/admin/ ./
COPY frontend/shared/ /build/shared/
RUN npm run build

FROM node:22-alpine AS miniapp-build
WORKDIR /build/miniapp
COPY frontend/miniapp/package*.json ./
RUN npm ci
COPY frontend/miniapp/ ./
COPY frontend/shared/ /build/shared/
RUN npm run build

FROM node:22-alpine AS web-build
WORKDIR /build/web
COPY frontend/web/package*.json ./
RUN npm ci
COPY frontend/web/ ./
COPY frontend/shared/ /build/shared/
COPY frontend/miniapp/src/assets/lotteries/ /build/miniapp/src/assets/lotteries/
RUN npm run build

FROM caddy:2.10-alpine
COPY infrastructure/Caddyfile /etc/caddy/Caddyfile
COPY --from=admin-build /build/admin/dist /srv/admin
COPY --from=miniapp-build /build/miniapp/dist /srv/miniapp
COPY --from=web-build /build/web/dist /srv/web
