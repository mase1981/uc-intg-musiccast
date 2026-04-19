"""
MusicCast integration driver.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi_framework import BaseIntegrationDriver

from uc_intg_musiccast.config import MusicCastConfig
from uc_intg_musiccast.device import MusicCastDevice
from uc_intg_musiccast.media_player_entity import MusicCastMediaPlayer
from uc_intg_musiccast.remote_entity import MusicCastRemote
from uc_intg_musiccast.sensor_entity import create_sensors
from uc_intg_musiccast.select_entity import create_selects

_LOG = logging.getLogger(__name__)


class MusicCastDriver(BaseIntegrationDriver[MusicCastDevice, MusicCastConfig]):
    """MusicCast integration driver."""

    def __init__(self):
        super().__init__(
            device_class=MusicCastDevice,
            entity_classes=[
                MusicCastMediaPlayer,
                MusicCastRemote,
                lambda cfg, dev: create_sensors(cfg, dev),
                lambda cfg, dev: create_selects(cfg, dev),
            ],
            driver_id="uc-intg-musiccast",
            require_connection_before_registry=True,
        )
