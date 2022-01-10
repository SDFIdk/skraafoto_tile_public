"""A utility to dump tiles directly from a tiff file on a http server."""

import logging
import aiohttp

from aiocogdumper.errors import TIFFError
from aiocogdumper.cog_tiles import AbstractReader

logger = logging.getLogger(__name__)


class Reader(AbstractReader):
    """Wraps the remote COG."""

    def __init__(
        self,
        url,
        httpsession: aiohttp.ClientSession,
        user=None,
        password=None,
    ):

        self.url = url
        self.session = httpsession
        # if user:
        #     self.auth = HTTPBasicAuth(user, password)
        # else:
        #     self.auth = None

        # self._resource_exists = True

        # self.session = requests.Session()
        # r = self.session.head(self.url, auth=self.auth)
        # if r.status_code != requests.codes.ok:
        #     self._resource_exists = False

    # @property
    # def resource_exists(self):
    #     return self._resource_exists

    async def read(self, offset, length):
        start = offset
        stop = offset + length - 1
        logger.info(f"Reading bytes: {start} to {stop}")
        headers = {"Range": f"bytes={start}-{stop}"}
        # r = self.session.get(self.url, auth=self.auth, headers=headers)
        # if r.status_code != requests.codes.partial_content:
        r = await self.session.get(self.url, headers=headers)
        if r.status != 206:
            raise TIFFError(
                f"HTTP byte range {offset}-{length} "
                f"not available. HTTP code {r.status}"
            )
        else:
            return await r.read()
