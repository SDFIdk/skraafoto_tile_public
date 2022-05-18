"""A utility to dump tiles directly from a tiff file on a http server."""
from typing import Dict, Optional
import logging
import aiohttp

from aiocogdumper.errors import HTTPError
from aiocogdumper.cog_tiles import AbstractReader

logger = logging.getLogger(__name__)


class Reader(AbstractReader):
    """Wraps the remote COG."""

    def __init__(
        self,
        url,
        httpsession: aiohttp.ClientSession,
        headers: Optional[Dict[str, str]] = {},
    ):

        self.url = url
        self.session = httpsession
        self.headers = headers or {}

    async def read(self, offset, length):
        start = offset
        stop = offset + length - 1
        request_headers = dict(self.headers)
        request_headers["Range"] = f"bytes={start}-{stop}"
        r = await self.session.get(self.url, headers=request_headers)
        if r.status != 206:
            raise HTTPError(await r.text(), r.status)
        else:
            return await r.read()
