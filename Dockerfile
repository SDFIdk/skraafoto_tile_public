FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10 AS production

RUN apk add --no-cache --virtual .build-deps gcc g++ libc-dev make\
    && apk add --no-cache libjpeg-turbo \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir aiohttp==3.8.1 aiofiles==0.8.0 async-cache==1.1.1 PyTurboJPEG==1.6.5 loguru==0.5.3 \
    && apk del .build-deps gcc g++ libc-dev make

ENV LIBTURBOJPEG=/usr/lib/libturbojpeg.so.0

COPY ./src/cogtiler /app

CMD ["python","-m","uvicorn","main:app","--host","0.0.0.0","--port","8000","--timeout-keep-alive","65"]
