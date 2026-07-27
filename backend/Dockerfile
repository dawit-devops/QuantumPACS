# syntax=docker/dockerfile:1

# ---- Stage 1: Python dependencies ----
FROM python:3.13-slim AS deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc musl-dev make \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir \
    --target=/install \
    -r /tmp/requirements.txt \
    && rm -rf /root/.cache/pip \
    && find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null \
    && find /install -type f -name "*.pyc" -delete

RUN find /install/bin -type f -exec sed -i '1s|^#!/usr/local/bin/python[0-9.]*$|#!/usr/bin/python3|' {} + 2>/dev/null || true

# ---- Stage 2: Production ----
FROM gcr.io/distroless/python3:nonroot

ARG VERSION=0.0.0
ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.title="QuantumPACS Backend" \
      org.opencontainers.image.description="QuantumPACS medical image management backend" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    QUANTUMPACS_DOCKER=true \
    PYTHONPATH=/app/packages \
    PATH=/app/packages/bin:$PATH

COPY --link --from=deps /install/ /app/packages

COPY --link --chown=65532:65532 . /quantumpacs/backend

WORKDIR /quantumpacs/backend
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v2/health')"]

CMD ["/quantumpacs/backend/docker_entrypoint.py"]