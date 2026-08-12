FROM python:3.14-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim AS runtime
WORKDIR /app
# Match the root image: unbuffered logs reach the Docker log pipe promptly.
ENV PYTHONUNBUFFERED=1
# curl: used by the compose healthcheck (the slim base ships no curl);
# tini: reaps orphaned workers and forwards signals to uvicorn as PID 1.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY . .
# routes.py mounts StaticFiles('static') when QUANTUMPACS_DOCKER=true —
# the dir is gitignored (dev-only docs.html/openapi.json) so the image must
# create it or the app crashes at import (caught by docker-smoke, D-M11).
RUN mkdir -p static
RUN groupadd -r quantumpacs && useradd -r -g quantumpacs -d /app -s /sbin/nologin -u 10001 quantumpacs && \
    chown -R quantumpacs:quantumpacs /app
# The entrypoint runs `python -m alembic upgrade head` (fail-fast, see
# docker-entrypoint.sh) before launching the app — mirrors the root
# single-image entrypoint (H6).
RUN chmod +x docker-entrypoint.sh
USER quantumpacs
EXPOSE 8080
# `python -m uvicorn` instead of the bare `uvicorn` console script: the
# builder's /usr/local/bin is not copied into the runtime image, so the
# entry point script would be missing (D-M11 docker-smoke caught this).
ENTRYPOINT ["/usr/bin/tini", "--", "./docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
