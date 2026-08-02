FROM python:3.14-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY . .
# routes.py mounts StaticFiles('static') when QUANTUMPACS_DOCKER=true —
# the dir is gitignored (dev-only docs.html/openapi.json) so the image must
# create it or the app crashes at import (caught by docker-smoke, D-M11).
RUN mkdir -p static
RUN groupadd -r quantumpacs && useradd -r -g quantumpacs -d /app -s /sbin/nologin -u 10001 quantumpacs && \
    chown -R quantumpacs:quantumpacs /app
USER quantumpacs
EXPOSE 8080
# `python -m uvicorn` instead of the bare `uvicorn` console script: the
# builder's /usr/local/bin is not copied into the runtime image, so the
# entry point script would be missing (D-M11 docker-smoke caught this).
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
