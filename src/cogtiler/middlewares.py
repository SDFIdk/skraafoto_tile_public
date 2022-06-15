import time

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Response, Request

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


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Set Cache-Control header for any successful GET (unless it was set before this middleware)."""

    HEADER_NAME = "Cache-Control"
    REQUEST_METHODS = ["GET", "HEAD"]

    def __init__(self, app, storage_directive: str = "public", max_age: int = None):
        super().__init__(app)
        self.storage_directive = storage_directive
        self.max_age = int(max_age) if max_age is not None else None
        value = self.storage_directive
        if max_age is not None:
            value += f", max-age={max_age}"
        self.cache_control_dict = {self.HEADER_NAME: value}
        logger.info(f"Adding cache-control middleware: [{value}]")

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if (
            self.HEADER_NAME not in response.headers
            and request.method in self.REQUEST_METHODS
            and response.status_code < 500
        ):
            response.headers.update(self.cache_control_dict)
        return response
