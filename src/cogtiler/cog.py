import aiohttp
from pydantic.fields import Field
from aiocogdumper.errors import TIFFError
from fastapi import Response, Query
from fastapi import security
from fastapi.params import Depends

from aiocogdumper.httpdumper import Reader as HttpReader
from aiocogdumper.filedumper import Reader as FileReader
from aiocogdumper.cog_tiles import COGTiff, Overflow
from cache import AsyncLRU
from pydantic import BaseModel


class CogRequest(BaseModel):
    url: str = Field(default=..., description="Url for cloud optimized geotiff")
    token: str = Depends(security.api_key.APIKeyQuery(name="token", auto_error=False))

    def get_cog_url(self) -> str:
        return self.url + f"?token={self.token}"


# Inspired by https://github.com/tiangolo/fastapi/issues/236
class HttpCogClient:
    def __init__(self, urlvalidator=None) -> None:
        # TODO: Configure whitelist
        pass

    def start(self):
        self.http_session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def stop(self):
        await self.http_session.close()
        self.http_session = None

    async def cog_from_query_param(
        self, cog_req: CogRequest = Depends(CogRequest)
    ) -> COGTiff:
        # TODO: Validate URL against whitelist or something
        return await self._get_http_cog(cog_req.get_cog_url(), self.http_session)

    async def get_tile_response(
        self, cog: COGTiff, z: int, x: int, y: int, overflow: Overflow = Overflow.Pad
    ) -> Response:
        try:
            mime_type, tilebytes = await cog.get_tile(x, y, z, overflow)
            return Response(content=tilebytes, media_type="image/jpeg")
        except TIFFError as te:
            return Response(content=te.message, status_code=500)

    @AsyncLRU(maxsize=1024)
    async def _get_http_cog(self, url: str, session: aiohttp.ClientSession) -> COGTiff:
        reader = HttpReader(url, session)
        return COGTiff(reader.read)