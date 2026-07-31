FROM python:3.14-slim

RUN apt-get update && apt-get install -y gcc musl-dev make && rm -rf /var/lib/apt/lists/* \
&& pip3 install --no-cache-dir \
'aiobotocore>=2.16.0,<3.0.0' \
aiofiles>=23.0.0 \
asyncpg>=0.29.0 \
'b2sdk>=2.0.0,<3.0.0' \
gunicorn>=22.0.0 \
'elasticsearch>=8.0,<9.0' \
'email-validator>=2.0.0' \
pydicom>=2.4.0 \
pynetdicom>=2.0.0 \
'PyJWT>=2.0,<3.0' \
PyPika>=0.48.0 \
PyYAML>=6.0 \
python-dateutil>=2.8.0 \
python-multipart>=0.0.5 \
'starlette>=0.35.0,<0.36.0' \
ujson>=5.0.0 \
uvicorn>=0.24.0 \
&& apt-get remove -y gcc musl-dev make && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ADD ./ /quantumpacs

WORKDIR /quantumpacs

ENV QUANTUMPACS_DOCKER=true

CMD ./start.sh
