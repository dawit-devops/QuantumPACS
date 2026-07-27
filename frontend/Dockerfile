# syntax=docker/dockerfile:1

# ---- Stage 1: Build ----
FROM node:22-alpine AS builder

ARG VERSION=0.0.0

WORKDIR /build
COPY --link package*.json ./
RUN npm ci --legacy-peer-deps
COPY --link . .

RUN npm run build

# ---- Stage 2: Runtime ----
FROM nginx:1.27-alpine AS production

ARG VERSION=0.0.0
ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.title="QuantumPACS Frontend" \
      org.opencontainers.image.description="QuantumPACS medical image management frontend" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.licenses="MIT"

COPY --link nginx.conf /etc/nginx/nginx.conf
COPY --link --from=builder /build/dist /usr/share/nginx/html
COPY --link docker-entrypoint.sh /docker-entrypoint.sh

RUN rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /var/cache/nginx \
    && chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/nginx.conf /docker-entrypoint.sh /var/cache/nginx \
    && chmod 644 /etc/nginx/nginx.conf \
    && chmod 755 /docker-entrypoint.sh

EXPOSE 80

USER nginx

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]