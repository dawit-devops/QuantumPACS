FROM python:3.14-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY . .
RUN groupadd -r quantumpacs && useradd -r -g quantumpacs -d /app -s /sbin/nologin -u 10001 quantumpacs && \
    chown -R quantumpacs:quantumpacs /app
USER quantumpacs
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
