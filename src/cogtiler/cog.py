from typing import Optional, Dict
import aiohttp
from pydantic import BaseModel, HttpUrl, validator
from pydantic.fields import Field
from fastapi import Response, Query, security
from fastapi.exceptions import HTTPException
from fastapi.params import Depends

from aiocogdumper.errors import TIFFError
from aiocogdumper.httpdumper import Reader as HttpReader
from aiocogdumper.cog_tiles import COGTiff, Overflow
from cache import AsyncLRU


from settings import get_settings


class CogRequest(BaseModel):
    url: HttpUrl = Field(
        default=Query(
            ...,
            description="Url for Cloud Optimized GeoTIFF (COG). Must be JPEG compressed.",
        )
    )
    query_token: Optional[str] = Depends(
        security.api_key.APIKeyQuery(name="token", auto_error=False)
    )
    header_token: Optional[str] = Depends(
        security.api_key.APIKeyHeader(name="token", auto_error=False)
    )

    def get_token(self) -> str:
        return self.query_token or self.header_token or ""

    def get_cog_url(self) -> str:
        return str(self.url)

    @validator("url")
    def url_in_whitelist(cls, value):
        settings = get_settings()
        if not settings.whitelist:
            return value
        for whitelisted in settings.whitelist:
            if value.startswith(whitelisted):
                return value
        raise HTTPException(403, "Specified URL is not allowed")


# Inspired by https://github.com/tiangolo/fastapi/issues/236
class HttpCogClient:
    def __init__(self, timeout: float = 10.0) -> None:
        """_summary_

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds for each http request for COG data, by default 10.0
        """
        self.http_session = None
        self.timeout_s = float(timeout)

    def start(self):
        self.http_session: aiohttp.ClientSession = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout_s)
        )

    async def stop(self):
        await self.http_session.close()
        self.http_session = None

    async def cog_from_query_param(
        self, cog_req: CogRequest = Depends(CogRequest)
    ) -> COGTiff:
        token = cog_req.get_token()
        headers = {"token": token} if token else {}
        return await self._get_http_cog(cog_req.get_cog_url(), headers)

    async def get_tile_response(
        self, cog: COGTiff, z: int, x: int, y: int, overflow: Overflow = Overflow.Pad
    ) -> Response:
        mime_type, tilebytes = await cog.get_tile(x, y, z, overflow)
        return Response(content=tilebytes, media_type="image/jpeg")

    @AsyncLRU(maxsize=1024)
    async def _get_http_cog(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> COGTiff:
        reader = HttpReader(url, self.http_session, headers)
        cog = COGTiff(reader.read)
        # parse header here to know if it throws. If it does throw it will not be cached
        await cog.read_header()
        return cog
