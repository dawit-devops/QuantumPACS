# syntax=docker/dockerfile:1

# ---- Stage 1: Frontend build ----
FROM node:22-alpine AS frontend

WORKDIR /build
COPY --link frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY --link frontend/ .
RUN npm run build

# ---- Stage 2: Python dependencies ----
FROM python:3.13-slim AS deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc musl-dev make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install
COPY --link backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir \
    --target=/install \
    -r /tmp/requirements.txt \
    && rm -rf /root/.cache/pip \
    && find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null \
    && find /install -type f -name "*.pyc" -delete

RUN find /install/bin -type f -exec sed -i '1s|^#!/usr/local/bin/python[0-9.]*$|#!/usr/bin/python3|' {} + 2>/dev/null || true

# ---- Stage 3: Tools (Caddy + tini) ----
FROM alpine:3.20 AS tools

RUN apk add --no-cache curl ca-certificates

ARG TINI_VERSION=0.19.0

RUN curl -fsSL "https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini-static-amd64" -o /tini \
    && chmod +x /tini

RUN curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o /caddy \
    && chmod +x /caddy

# ---- Stage 4: Production ----
FROM gcr.io/distroless/python3:nonroot

ARG VERSION=0.0.0
ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.title="QuantumPACS" \
      org.opencontainers.image.description="Production PACS for medical image management" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    QUANTUMPACS_DOCKER=true \
    PYTHONPATH=/app/packages \
    PATH=/app/packages/bin:$PATH

COPY --link --from=tools /tini /usr/bin/tini
COPY --link --from=tools /caddy /usr/bin/caddy
COPY --link --from=tools /etc/ssl/certs /etc/ssl/certs

COPY --link --from=deps /install/ /app/packages

COPY --link --from=frontend /build/dist /quantumpacs/frontend/dist

COPY --link --chown=65532:65532 backend/ /quantumpacs/backend
COPY --link Caddyfile /etc/caddy/Caddyfile
COPY --link docker_entrypoint.py /docker_entrypoint.py

WORKDIR /quantumpacs/backend
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost/api/v2/health')"]

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "/docker_entrypoint.py"]