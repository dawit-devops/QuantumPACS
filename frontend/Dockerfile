FROM node:22-alpine@sha256:76789712cd1ae89a1225eac9077010d68987a423588042dac30446f502f1858c AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM nginx:1.27-alpine@sha256:62223d644fa234c3a1cc785ee14242ec47a77364226f1c811d2f669f96dc2ac8 AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Non-root nginx: bind 8080 (>=1024) as user nginx, and make the pid/log/cache
# paths it owns writable so the master process can start unprivileged.
RUN apk add --no-cache curl \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /var/log/nginx
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fs http://127.0.0.1:8080/ || exit 1
