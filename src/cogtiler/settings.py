from functools import lru_cache
from typing import Set
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

    class Config:
        env_prefix = "cogtiler_"
