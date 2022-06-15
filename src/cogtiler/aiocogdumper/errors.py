"""TIFF read exceptions."""


class HTTPError(Exception):
    """Represents an upstream http error"""

    exit_code = 1

    def __init__(self, message, status=None):
        self.message = message
        self.status = status


class HTTPRangeNotSupportedError(Exception):
    """Represents an error indicating missing upstram support for http range requests"""

    exit_code = 1


class TIFFError(Exception):
    exit_code = 1

    def __init__(self, message):
        self.message = message


class JPEGError(Exception):
    exit_code = 1

    def __init__(self, message):
        self.message = message
