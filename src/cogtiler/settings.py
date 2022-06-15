from functools import lru_cache
from typing import Set, Optional
from pydantic import BaseSettings, HttpUrl


@lru_cache()
def get_settings():
    return Settings()


class Settings(BaseSettings):
    """Settings of the cogtiler API

    Uses pydantic BaseSettings: https://pydantic-docs.helpmanual.io/usage/settings/
    """

    whitelist: Set[HttpUrl] = set()
    debug: bool = False
    request_timeout: float = 10
    cache_max_age: Optional[int] = 60 * 60 * 24

    class Config:
        env_prefix = "cogtiler_"
