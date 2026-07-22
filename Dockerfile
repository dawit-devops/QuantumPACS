# ---- Frontend build ----
FROM node:26-alpine AS frontend

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# ---- Backend ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc musl-dev make && rm -rf /var/lib/apt/lists/* \
&& pip3 install --no-cache-dir \
'aiobotocore>=2.16.0,<3.0.0' \
aiofiles==0.4.0 \
asyncpg==0.18.3 \
'b2sdk>=2.0.0,<3.0.0' \
gunicorn==19.9.0 \
'elasticsearch>=8.0,<9.0' \
email-validator==1.0.4 \
pydicom==1.3.0 \
pynetdicom==1.4.1 \
'PyJWT>=2.0,<3.0' \
PyPika==0.35.2 \
PyYAML==5.1.2 \
python-dateutil==2.8.0 \
python-multipart==0.0.5 \
'starlette>=0.35.0,<0.36.0' \
ujson==1.35 \
uvicorn==0.8.6 \
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
