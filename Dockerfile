FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11-slim AS production

RUN apt update \
    && apt upgrade -y \
    && apt install libturbojpeg0 -y

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV LIBTURBOJPEG=/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0

COPY ./src/cogtiler /app

CMD ["python","-m","uvicorn","main:app","--host","0.0.0.0","--port","8000","--timeout-keep-alive","65", "--log-config", "log_conf.yml"]
