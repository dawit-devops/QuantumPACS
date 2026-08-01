# Node pinned to 22.12.0 to match .nvmrc — CI installs the same version.
FROM node:22.12.0-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

# nginx runs as non-root (USER nginx); NGINX_PORT moves the listener off 80,
# and the pid file goes to /tmp (writable without superuser).
FROM nginx:1.27.4-alpine AS runtime
ENV NGINX_UID=101 \
    NGINX_GID=101 \
    NGINX_PORT=8080
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
