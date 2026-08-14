FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
# Plain `npm ci` — NOT --legacy-peer-deps: with the legacy flag npm's
# optional-dependency bug (npm/cli#4828) drops rolldown's native binding
# (@rolldown/binding-linux-x64-gnu), and the build then fails at the PWA
# closeBundle hook with ENOENT on dist/sw.js.
RUN npm ci
COPY . .
RUN npm run build

# nginxinc/nginx-unprivileged: master+workers run as uid 101 (non-root),
# listens on 8080 (>=1024 so no privileged bind needed).
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
