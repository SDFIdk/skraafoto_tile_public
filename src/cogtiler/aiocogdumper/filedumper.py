"""A utility to dump tiles directly from a local tiff file."""

import logging
from aiocogdumper.cog_tiles import AbstractReader
from pathlib import Path
import aiofiles

logger = logging.getLogger(__name__)


class Reader(AbstractReader):
    """Wraps the remote COG."""

    def __init__(self, path: Path):
        # TODO: Should we keep til reader instead of opening it each time?
        # Now we risc opening multiple times. If we keep the reader how do we make sure we dont get too many open reader and that it is closed correctly?
        self._path = path

    async def read(self, offset, length):
        async with aiofiles.open(self._path, mode="rb") as f:
            contents = await f.read()
            start = offset
            stop = offset + length - 1
            logger.info(f"Reading bytes: {start} to {stop}")
            await f.seek(offset)
            return await f.read(length)
