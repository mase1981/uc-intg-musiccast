"""
MusicCast media player entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi_framework import MediaPlayerEntity

from uc_intg_musiccast.config import MusicCastConfig
from uc_intg_musiccast.device import MusicCastDevice

_LOG = logging.getLogger(__name__)

FEATURES = [
    media_player.Features.ON_OFF,
    media_player.Features.TOGGLE,
    media_player.Features.PLAY_PAUSE,
    media_player.Features.STOP,
    media_player.Features.NEXT,
    media_player.Features.PREVIOUS,
    media_player.Features.VOLUME,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
    media_player.Features.MEDIA_TITLE,
    media_player.Features.MEDIA_ARTIST,
    media_player.Features.MEDIA_ALBUM,
    media_player.Features.MEDIA_IMAGE_URL,
    media_player.Features.MEDIA_DURATION,
    media_player.Features.MEDIA_POSITION,
    media_player.Features.REPEAT,
    media_player.Features.SHUFFLE,
    media_player.Features.SELECT_SOURCE,
    media_player.Features.SELECT_SOUND_MODE,
]


class MusicCastMediaPlayer(MediaPlayerEntity):
    """MusicCast media player entity."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"media_player.{device_config.identifier}"
        super().__init__(
            entity_id,
            device_config.name,
            FEATURES,
            {
                media_player.Attributes.STATE: media_player.States.UNKNOWN,
                media_player.Attributes.VOLUME: 0,
                media_player.Attributes.MUTED: False,
                media_player.Attributes.SOURCE: "",
                media_player.Attributes.SOURCE_LIST: [],
                media_player.Attributes.SOUND_MODE: "",
                media_player.Attributes.SOUND_MODE_LIST: [],
                media_player.Attributes.MEDIA_TITLE: "",
                media_player.Attributes.MEDIA_ARTIST: "",
                media_player.Attributes.MEDIA_ALBUM: "",
                media_player.Attributes.MEDIA_IMAGE_URL: "",
            },
            device_class=media_player.DeviceClasses.RECEIVER,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({media_player.Attributes.STATE: media_player.States.UNAVAILABLE})
            return

        if self._device.power == "standby":
            state = media_player.States.STANDBY
        elif self._device.playback == "play":
            state = media_player.States.PLAYING
        elif self._device.playback == "pause":
            state = media_player.States.PAUSED
        else:
            state = media_player.States.ON

        attrs = {
            media_player.Attributes.STATE: state,
            media_player.Attributes.VOLUME: self._device.volume_percent,
            media_player.Attributes.MUTED: self._device.muted,
            media_player.Attributes.SOURCE: self._device.input_source_name,
            media_player.Attributes.SOURCE_LIST: self._device.source_names,
            media_player.Attributes.SOUND_MODE: self._device.sound_program_name,
            media_player.Attributes.SOUND_MODE_LIST: self._device.sound_mode_names,
        }

        if state in (media_player.States.PLAYING, media_player.States.PAUSED):
            attrs[media_player.Attributes.MEDIA_TITLE] = self._device.track
            attrs[media_player.Attributes.MEDIA_ARTIST] = self._device.artist
            attrs[media_player.Attributes.MEDIA_ALBUM] = self._device.album
            attrs[media_player.Attributes.MEDIA_IMAGE_URL] = self._device.albumart_url
            attrs[media_player.Attributes.MEDIA_DURATION] = self._device.total_time
            attrs[media_player.Attributes.MEDIA_POSITION] = self._device.play_time
            attrs[media_player.Attributes.REPEAT] = self._device.repeat
            attrs[media_player.Attributes.SHUFFLE] = self._device.shuffle
        else:
            attrs[media_player.Attributes.MEDIA_TITLE] = ""
            attrs[media_player.Attributes.MEDIA_ARTIST] = ""
            attrs[media_player.Attributes.MEDIA_ALBUM] = ""
            attrs[media_player.Attributes.MEDIA_IMAGE_URL] = ""

        self.update(attrs)

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        try:
            match cmd_id:
                case media_player.Commands.ON:
                    await self._device.set_power("on")
                case media_player.Commands.OFF:
                    await self._device.set_power("standby")
                case media_player.Commands.TOGGLE:
                    await self._device.set_power("toggle")
                case media_player.Commands.PLAY_PAUSE:
                    await self._device.set_playback("play_pause")
                case media_player.Commands.STOP:
                    await self._device.set_playback("stop")
                case media_player.Commands.NEXT:
                    await self._device.set_playback("next")
                case media_player.Commands.PREVIOUS:
                    await self._device.set_playback("previous")
                case media_player.Commands.VOLUME:
                    if params and "volume" in params:
                        await self._device.set_volume(int(params["volume"]))
                case media_player.Commands.VOLUME_UP:
                    await self._device.volume_up()
                case media_player.Commands.VOLUME_DOWN:
                    await self._device.volume_down()
                case media_player.Commands.MUTE_TOGGLE:
                    await self._device.set_mute(not self._device.muted)
                case media_player.Commands.REPEAT:
                    if params and "repeat" in params:
                        repeat_map = {"OFF": "off", "ONE": "one", "ALL": "all"}
                        await self._device.set_repeat(repeat_map.get(params["repeat"], "off"))
                case media_player.Commands.SHUFFLE:
                    if params and "shuffle" in params:
                        await self._device.set_shuffle("on" if params["shuffle"] else "off")
                case media_player.Commands.SELECT_SOURCE:
                    if params and "source" in params:
                        source_id = self._device.get_input_id_by_name(params["source"])
                        if source_id:
                            await self._device.set_input(source_id)
                        else:
                            return StatusCodes.BAD_REQUEST
                case media_player.Commands.SELECT_SOUND_MODE:
                    if params and "mode" in params:
                        program_id = self._device.get_program_id_by_name(params["mode"])
                        if program_id:
                            await self._device.set_sound_program(program_id)
                        else:
                            return StatusCodes.BAD_REQUEST
                case _:
                    return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except Exception as err:
            _LOG.error("[%s] Command %s failed: %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR
