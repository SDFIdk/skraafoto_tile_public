from asyncio.exceptions import TimeoutError
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler

from aiocogdumper.errors import HTTPError, TIFFError, HTTPRangeNotSupportedError

from loguru import logger


async def upstream_http_exception_handler(request, exc: HTTPError):
    """Handle http exceptions from upstream server"""
    logger.warning(f"Upstream HTTP error [{request.query_params['url']}]: {repr(exc)}")
    # Convert to FastApi exception
    exc = HTTPException(502, f"Upstream server returned: [{exc.status}] {exc.message}")
    return await http_exception_handler(request, exc)


async def upstream_range_not_supported_exception_handler(
    request, exc: HTTPRangeNotSupportedError
):
    """Handle range request not supported exceptions"""
    logger.warning(
        f"Upstream server does not support range requests: [{request.query_params['url']}]"
    )
    # Convert to FastApi exception
    exc = HTTPException(502, f"Upstream server does not support http range requests")
    return await http_exception_handler(request, exc)


async def upstream_tiff_exception_handler(request, exc: TIFFError):
    """Handle tiff exceptions"""
    logger.warning(
        f"Tiff error when reading [{request.query_params['url']}]: {repr(exc)}"
    )
    # Convert to FastApi exception
    exc = HTTPException(500, f"Error reading upstream tiff file: {exc.message}")
    return await http_exception_handler(request, exc)


async def upstream_timeout_exception_handler(request, exc: TimeoutError):
    """Handle http timeout exceptions"""
    logger.warning(f"Timeout when reading [{request.query_params['url']}]: {repr(exc)}")
    # Convert to FastApi exception
    exc = HTTPException(504, f"Timeout getting upstream tiff file data")
    return await http_exception_handler(request, exc)


# All custom exception handlers
all_exception_handlers = {
    HTTPError: upstream_http_exception_handler,
    HTTPRangeNotSupportedError: upstream_range_not_supported_exception_handler,
    TIFFError: upstream_tiff_exception_handler,
    TimeoutError: upstream_timeout_exception_handler,
}
