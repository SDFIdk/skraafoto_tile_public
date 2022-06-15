import time

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Query, Path, Response, Request

from loguru import logger


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Middleware adding processing time to response header and logs"""

    def __init__(
        self,
        app,
    ):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        end = time.perf_counter()
        process_time = f"{(end - start) * 1000:0.1f} ms"
        logger.debug("{} {} {}", request.method, request.url, process_time)
        response.headers["X-Process-Time"] = process_time
        return response
