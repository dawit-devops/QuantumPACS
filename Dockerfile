# ---- Frontend build ----
FROM node:26-alpine AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# ---- Backend ----
FROM python:3.11-slim

COPY backend/requirements.txt /tmp/requirements.txt
RUN apt-get update && apt-get install -y gcc musl-dev make && rm -rf /var/lib/apt/lists/* \
&& pip3 install --no-cache-dir -r /tmp/requirements.txt \
&& apt-get remove -y gcc musl-dev make && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# ---- Install Caddy for serving frontend + reverse proxy ----
RUN apt-get update && apt-get install -y caddy && rm -rf /var/lib/apt/lists/*

COPY backend/ /openpacs/backend
COPY --from=frontend /build/dist /openpacs/frontend/dist

WORKDIR /openpacs/backend
ENV OPENPACS_DOCKER=true

COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80
CMD caddy run --config /etc/caddy/Caddyfile &
gunicorn app:app -k uvicorn.workers.UvicornWorker -c api_conf.py &
wait
