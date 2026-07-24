# ---- Stage 1: Frontend build ----
FROM node:22-alpine AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python dependencies ----
FROM python:3.12-slim AS deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc musl-dev make \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && apt-get remove -y gcc musl-dev make \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ---- Stage 3: Production ----
FROM python:3.12-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    caddy ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY backend/ /quantumpacs/backend
COPY --from=frontend /build/dist /quantumpacs/frontend/dist
COPY Caddyfile /etc/caddy/Caddyfile

RUN addgroup --system --gid 1001 quantumpacs \
    && adduser --system --uid 1001 --ingroup quantumpacs --no-create-home quantumpacs \
    && mkdir -p /data/caddy /quantumpacs/storage \
    && chown -R quantumpacs:quantumpacs /quantumpacs /data/caddy /etc/caddy

WORKDIR /quantumpacs/backend
ENV QUANTUMPACS_DOCKER=true

EXPOSE 80

USER quantumpacs

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost/api/health || exit 1

COPY docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/docker-entrypoint.sh"]
