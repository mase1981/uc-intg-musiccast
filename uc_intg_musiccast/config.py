"""
MusicCast configuration module.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass

from ucapi_framework import BaseConfigManager


@dataclass
class MusicCastConfig:
    identifier: str = ""
    name: str = ""
    address: str = ""
    port: int = 80
    use_ssl: bool = False


class MusicCastConfigManager(BaseConfigManager[MusicCastConfig]):
    pass
