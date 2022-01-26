"""Function for extracting tiff tiles."""

from enum import Enum
import os

from abc import abstractmethod
from math import ceil
import struct

from aiocogdumper.errors import TIFFError
from aiocogdumper.jpegreader import insert_tables
from aiocogdumper.tifftags import compression as CompressionType
from aiocogdumper.tifftags import sizes as TIFFSizes
from aiocogdumper.tifftags import tags as TIFFTags


class AbstractReader:  # pragma: no cover
    @abstractmethod
    async def read(offset, len):
        pass


from enum import Enum

# What to do about tile overflow
class Overflow(Enum):
    Pad = "pad"
    Crop = "crop"
    Mask = "mask"


class COGTiff:
    """
    Cloud Optimised GeoTIFF
    -----
    Format
        TIFF / BigTIFF signature
        IFD (Image File Directory) of full resolution image
        Values of TIFF tags that don't fit inline in the IFD directory, such as TileOffsets, TileByteCounts and GeoTIFF keys
        Optional: IFD (Image File Directory) of first overview (typically subsampled by a factor of 2), followed by the values of its tags that don't fit inline
        Optional: IFD (Image File Directory) of second overview (typically subsampled by a factor of 4), followed by the values of its tags that don't fit inline
        ...
        Optional: IFD (Image File Directory) of last overview (typically subsampled by a factor of 2N), followed by the values of its tags that don't fit inline
        Optional: tile content of last overview level
        ...
        Optional: tile content of first overview level
        Tile content of full resolution image.
    """

    def __init__(self, reader):
        """Parses a (Big)TIFF for image tiles.
        Parameters
        ----------
        reader:
            A reader that implements the cogdumper.cog_tiles.AbstractReader methods
        """
        self._endian = "<"
        self._version = 42
        self.read = reader
        self._big_tiff = False
        self.header = ""
        self._offset = 0
        self._image_ifds = []
        self._mask_ifds = []
        self._header_is_parsed = False

        # self.read_header()

    async def _ifds(self):
        """Reads TIFF image file directories from a COG recursively.
        Parameters
        -----------
        offset:
            number, offset into the tiff stream to read from, this is only
            required for the first image file directory
        overview:
            number, an identifier that is the overview level in the COG
            image pyramid
        Yield
        --------
        dict: Image File Directory for the next IFD
        """
        while self._offset != 0:
            next_offset = 0
            pos = 0
            tags = []

            fallback_size = 4096 if self._big_tiff else 1024
            if self._offset > len(self.header):
                byte_starts = len(self.header)
                byte_ends = byte_starts + self._offset + fallback_size
                self.header += await self.read(byte_starts, byte_ends)

            if self._big_tiff:
                bytes = self.header[self._offset : self._offset + 8]
                num_tags = struct.unpack(f"{self._endian}Q", bytes)[0]

                byte_starts = self._offset + 8
                byte_ends = (num_tags * 20) + 8 + byte_starts
                if byte_ends > len(self.header):
                    s = len(self.header)
                    self.header += await self.read(s, byte_ends)

                bytes = self.header[byte_starts:byte_ends]

                for t in range(0, num_tags):
                    code = struct.unpack(f"{self._endian}H", bytes[pos : pos + 2])[0]

                    if code in TIFFTags:
                        dtype = struct.unpack(
                            f"{self._endian}H", bytes[pos + 2 : pos + 4]
                        )[0]

                        if dtype not in TIFFSizes:  # pragma: no cover
                            raise TIFFError(f"Unrecognised data type {dtype}")

                        num_values = struct.unpack(
                            f"{self._endian}Q", bytes[pos + 4 : pos + 12]
                        )[0]
                        tag_len = num_values * TIFFSizes[dtype]["size"]
                        if tag_len <= 8:
                            data = bytes[pos + 12 : pos + 12 + tag_len]
                        else:  # pragma: no cover
                            data_offset = struct.unpack(
                                f"{self._endian}Q", bytes[pos + 12 : pos + 20]
                            )[0]

                            byte_starts = data_offset
                            byte_ends = byte_starts + tag_len
                            if byte_ends > len(self.header):
                                s = len(self.header)
                                self.header += await self.read(s, byte_ends)

                            data = self.header[byte_starts:byte_ends]

                        tags.append(
                            {
                                "code": code,
                                "dtype": TIFFSizes[dtype],
                                "num_values": num_values,
                                "data": data,
                            }
                        )

                    pos = pos + 20

                self._offset = self._offset + 8 + pos
                next_offset = struct.unpack(
                    f"{self._endian}Q", self.header[self._offset : self._offset + 8]
                )[0]
            else:
                bytes = self.header[self._offset : self._offset + 2]
                num_tags = struct.unpack(f"{self._endian}H", bytes)[0]

                byte_starts = self._offset + 2
                byte_ends = (num_tags * 12) + 2 + byte_starts
                if byte_ends > len(self.header):
                    s = len(self.header)
                    self.header += await self.read(s, byte_ends)

                bytes = self.header[byte_starts:byte_ends]

                for t in range(0, num_tags):
                    code = struct.unpack(f"{self._endian}H", bytes[pos : pos + 2])[0]

                    if code in TIFFTags:
                        dtype = struct.unpack(
                            f"{self._endian}H", bytes[pos + 2 : pos + 4]
                        )[0]

                        if dtype not in TIFFSizes:  # pragma: no cover
                            raise TIFFError(f"Unrecognised data type {dtype}")

                        num_values = struct.unpack(
                            f"{self._endian}L", bytes[pos + 4 : pos + 8]
                        )[0]
                        tag_len = num_values * TIFFSizes[dtype]["size"]
                        if tag_len <= 4:
                            data = bytes[pos + 8 : pos + 8 + tag_len]
                        else:
                            data_offset = struct.unpack(
                                f"{self._endian}L", bytes[pos + 8 : pos + 12]
                            )[0]

                            byte_starts = data_offset
                            byte_ends = byte_starts + tag_len
                            if byte_ends > len(self.header):
                                s = len(self.header)
                                self.header += await self.read(s, byte_ends)
                            data = self.header[byte_starts:byte_ends]

                        tags.append(
                            {
                                "code": code,
                                "dtype": TIFFSizes[dtype],
                                "num_values": num_values,
                                "data": data,
                            }
                        )

                    pos = pos + 12

                self._offset = self._offset + 2 + pos
                next_offset = struct.unpack(
                    f"{self._endian}L", self.header[self._offset : self._offset + 4]
                )[0]

            self._offset = next_offset

            yield {"tags": tags, "next_offset": next_offset}

    async def read_header(self):
        """Read and parse COG header."""
        if self._header_is_parsed:
            return
        buff_size = int(os.environ.get("COG_INGESTED_BYTES_AT_OPEN", "16384"))
        self.header = await self.read(0, buff_size)

        # read first 4 bytes to determine tiff or bigtiff and byte order
        if self.header[:2] == b"MM":
            self._endian = ">"

        self._version = struct.unpack(f"{self._endian}H", self.header[2:4])[0]

        if self._version == 42:
            # TIFF
            self._big_tiff = False
            # read offset to first IFD
            self._offset = struct.unpack(f"{self._endian}L", self.header[4:8])[0]
        elif self._version == 43:
            # BIGTIFF
            self._big_tiff = True
            bytes = self.header[4:16]
            bytesize = struct.unpack(f"{self._endian}H", bytes[0:2])[0]
            w = struct.unpack(f"{self._endian}H", bytes[2:4])[0]
            self._offset = struct.unpack(f"{self._endian}Q", bytes[4:])[0]
            if bytesize != 8 or w != 0:  # pragma: no cover
                raise TIFFError(
                    f"Invalid BigTIFF with bytesize {bytesize} and word {w}"
                )
        else:  # pragma: no cover
            raise TIFFError(f"Invalid version {self._version} for TIFF file")

        self._init = True

        # for JPEG we need to read all IFDs, they are at the front of the file
        async for ifd in self._ifds():
            mime_type = "image/jpeg"
            # tile offsets are an extension but if they aren't in the file then
            # you can't get a tile back!
            offsets = []
            byte_counts = []
            image_width = 0
            image_height = 0
            tile_width = 0
            tile_height = 0
            jpeg_tables = None

            for t in ifd["tags"]:
                code = t["code"]
                fmt = t["dtype"]["format"]
                if code == 256:
                    # image width
                    image_width = struct.unpack(f"{self._endian}{fmt}", t["data"])[0]
                elif code == 257:
                    # image height
                    image_height = struct.unpack(f"{self._endian}{fmt}", t["data"])[0]
                elif code == 259:
                    # compression
                    val = struct.unpack(f"{self._endian}{fmt}", t["data"])[0]
                    if val in CompressionType:
                        mime_type = CompressionType[val]
                    else:
                        mime_type = "application/octet-stream"
                elif code == 322:
                    # tile width
                    tile_width = struct.unpack(f"{self._endian}{fmt}", t["data"])[0]
                elif code == 323:
                    # tile height
                    tile_height = struct.unpack(f"{self._endian}{fmt}", t["data"])[0]
                elif code == 324:
                    # tile offsets
                    offsets = struct.unpack(
                        f'{self._endian}{t["num_values"]}{fmt}', t["data"]
                    )
                elif code == 325:
                    # tile byte counts
                    byte_counts = struct.unpack(
                        f'{self._endian}{t["num_values"]}{fmt}', t["data"]
                    )
                elif code == 347:
                    # JPEG Tables
                    jpeg_tables = t["data"]

            if len(offsets) == 0:
                raise TIFFError("TIFF Tiles are not found in IFD {z}")

            ifd["image_width"] = image_width
            ifd["image_height"] = image_height
            ifd["compression"] = mime_type
            ifd["tile_width"] = tile_width
            ifd["tile_height"] = tile_height
            ifd["offsets"] = offsets
            ifd["byte_counts"] = byte_counts
            ifd["jpeg_tables"] = jpeg_tables

            ifd["nx_tiles"] = ceil(image_width / float(tile_width))
            ifd["ny_tiles"] = ceil(image_height / float(tile_height))

            if ifd["compression"] == "deflate":
                self._mask_ifds.append(ifd)
            else:
                self._image_ifds.append(ifd)

        if len(self._image_ifds) == 0 and len(self._mask_ifds) > 0:  # pragma: no cover
            self._image_ifds = self._mask_ifds
            self._mask_ifds = []

        # Done parsing header. Dont spend time parsing it again.
        self._header_is_parsed = True

    async def get_info(self, z=0):
        await self.read_header()
        image_ifd = self._image_ifds[z]
        return {
            "width": image_ifd["image_width"],
            "height": image_ifd["image_height"],
            "compression": image_ifd["compression"],
            "tile_width": image_ifd["tile_width"],
            "tile_height": image_ifd["tile_height"],
            "tile_cols": image_ifd["nx_tiles"],
            "tile_rows": image_ifd["ny_tiles"],
            # Should this be a list of overviews?
            "overviews": len(self._image_ifds) - z - 1,
        }

    async def get_tile(self, x: int, y: int, z: int, overflow: Overflow = Overflow.Pad):
        """Read tile data."""
        await self.read_header()
        if z < len(self._image_ifds):
            image_ifd = self._image_ifds[z]
            if y >= image_ifd["ny_tiles"] or x >= image_ifd["nx_tiles"]:
                raise TIFFError(f"Tile {x} {y} is out of bounds for overview {z}")
            # TODO: Handle different block orders!
            idx = (y * image_ifd["nx_tiles"]) + x
            if idx > len(image_ifd["offsets"]):
                raise TIFFError(f"Tile {x} {y} {z} does not exist")
            offset = image_ifd["offsets"][idx]
            byte_count = image_ifd["byte_counts"][idx]
            tile = await self.read(offset, byte_count)
            if image_ifd["compression"] == "image/jpeg":
                # fix up jpeg tile with missing quantization tables
                tile = insert_tables(tile, image_ifd["jpeg_tables"])
                # look for a bit mask file
                if z < len(self._mask_ifds):
                    mask_ifd = self._mask_ifds[z]
                    mask_offset = mask_ifd["offsets"][idx]
                    mask_byte_count = mask_ifd["byte_counts"][idx]
                    mask_tile = await self.read(mask_offset, mask_byte_count)
                    tile = tile + mask_tile
                # If we are at the last tile row or col we may have to do somethong about the padded area
                if overflow != Overflow.Pad and (
                    x == image_ifd["nx_tiles"] - 1 or y == image_ifd["ny_tiles"] - 1
                ):
                    from_col = (
                        image_ifd["image_width"] - image_ifd["tile_width"] * x + 1
                    )
                    from_row = (
                        image_ifd["image_height"] - image_ifd["tile_height"] * y + 1
                    )
                    if overflow == Overflow.Mask:
                        tile = mask_padded_jpeg(
                            tile,
                            image_ifd["tile_height"],
                            image_ifd["tile_width"],
                            from_row,
                            from_col,
                        )
                    elif overflow == Overflow.Crop:
                        tile = crop_padded_jpeg(
                            tile,
                            image_ifd["tile_height"],
                            image_ifd["tile_width"],
                            from_row,
                            from_col,
                        )
                return image_ifd["compression"], tile
            else:
                return image_ifd["compression"], tile
        else:
            raise TIFFError(f"Overview {z} is out of bounds.")

    @property
    def version(self):
        return self._version


from turbojpeg import TurboJPEG
import os

# The python module cannot find the correct libpath on alpine
LIBTURBOJPEG = os.getenv("LIBTURBOJPEG")


def mask_padded_jpeg(
    jpegbytes, tile_height, tile_width, from_row, from_col, mask_value=0
):
    # TODO: Should this be made async. Maybe like https://stackoverflow.com/a/53563478
    if not 0 <= from_row < tile_height and not 0 <= from_col < tile_width:
        return jpegbytes
    turbojpeg = TurboJPEG(LIBTURBOJPEG)
    bgr_array = turbojpeg.decode(jpegbytes)
    if 0 <= from_row < tile_height:
        bgr_array[from_row:, :, :] = mask_value
    if 0 <= from_col < tile_width:
        bgr_array[:, from_col:, :] = mask_value
    return turbojpeg.encode(bgr_array)


def crop_padded_jpeg(jpegbytes, tile_height, tile_width, from_row, from_col):
    # TODO: Should this be made async. Maybe like https://stackoverflow.com/a/53563478
    if not 0 <= from_row < tile_height and not 0 <= from_col < tile_width:
        return jpegbytes
    turbojpeg = TurboJPEG(LIBTURBOJPEG)
    return turbojpeg.crop(jpegbytes, 0, 0, from_col - 1, from_row - 1)
