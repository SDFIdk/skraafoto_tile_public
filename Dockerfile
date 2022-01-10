FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10 AS production

RUN apk add --no-cache --virtual .build-deps gcc g++ libc-dev make\
    && apk add --no-cache libjpeg-turbo \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir aiohttp==3.8.1 aiofiles==0.8.0 async-cache==1.1.1 PyTurboJPEG==1.6.3 loguru==0.5.3 \
    && apk del .build-deps gcc g++ libc-dev make

ENV LIBTURBOJPEG=/usr/lib/libturbojpeg.so.0

COPY ./src/cogtiler /app

FROM production as debug
# This enables vscode to do debugging inside container
# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser