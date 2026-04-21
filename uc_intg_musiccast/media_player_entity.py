"""
MusicCast media player entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi.media_player import (
    BrowseMediaItem,
    BrowseOptions,
    BrowseResults,
    MediaClass,
    Pagination,
)
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
    media_player.Features.BROWSE_MEDIA,
    media_player.Features.PLAY_MEDIA,
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
            repeat_map = {"off": "OFF", "one": "ONE", "all": "ALL"}
            attrs[media_player.Attributes.REPEAT] = repeat_map.get(self._device.repeat, "OFF")
            attrs[media_player.Attributes.SHUFFLE] = self._device.shuffle
        else:
            attrs[media_player.Attributes.MEDIA_TITLE] = ""
            attrs[media_player.Attributes.MEDIA_ARTIST] = ""
            attrs[media_player.Attributes.MEDIA_ALBUM] = ""
            attrs[media_player.Attributes.MEDIA_IMAGE_URL] = ""

        self.update(attrs)

    async def browse(self, options: BrowseOptions) -> BrowseResults | StatusCodes:
        media_type = options.media_type or "root"
        media_id = options.media_id or ""
        page = options.paging.page if options.paging else 1
        limit = options.paging.limit if options.paging else 20

        if media_type == "root" or (options.media_id is None and options.media_type is None):
            return self._browse_root()
        if media_type == "sources":
            return self._browse_sources(page, limit)
        if media_type == "presets":
            return self._browse_presets(page, limit)
        if media_type == "sound_programs":
            return self._browse_sound_programs()
        if media_type == "netusb":
            return await self._browse_netusb(media_id, page)

        return StatusCodes.NOT_FOUND

    def _browse_root(self) -> BrowseResults:
        items = [
            BrowseMediaItem(
                media_id="sources",
                title="Sources",
                media_type="sources",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                can_play=False,
                thumbnail="icon://uc:music",
            ),
            BrowseMediaItem(
                media_id="presets",
                title="Presets / Favorites",
                media_type="presets",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                can_play=False,
                thumbnail="icon://uc:radio",
            ),
        ]
        if self._device.available_sound_programs:
            items.append(BrowseMediaItem(
                media_id="sound_programs",
                title="Sound Programs",
                media_type="sound_programs",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                can_play=False,
                thumbnail="icon://uc:equalizer",
            ))
        return BrowseResults(
            media=BrowseMediaItem(
                media_id="root",
                title="MusicCast",
                media_type="root",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                items=items,
            ),
            pagination=Pagination(page=1, limit=len(items), count=len(items)),
        )

    def _browse_sources(self, page: int, limit: int) -> BrowseResults:
        all_sources = self._device.available_inputs
        start = (page - 1) * limit
        page_sources = all_sources[start: start + limit]
        items = []
        for src in page_sources:
            is_netusb = src.get("play_info_type") == "netusb"
            if is_netusb:
                items.append(BrowseMediaItem(
                    media_id=f"netusb:{src['id']}",
                    title=src["name"],
                    media_type="netusb",
                    media_class=MediaClass.DIRECTORY,
                    can_browse=True,
                    can_play=True,
                ))
            else:
                items.append(BrowseMediaItem(
                    media_id=f"source:{src['id']}",
                    title=src["name"],
                    media_type="source",
                    media_class=MediaClass.CHANNEL,
                    can_browse=False,
                    can_play=True,
                ))
        return BrowseResults(
            media=BrowseMediaItem(
                media_id="sources",
                title="Sources",
                media_type="sources",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                items=items,
            ),
            pagination=Pagination(page=page, limit=limit, count=len(all_sources)),
        )

    async def _browse_netusb(self, media_id: str, page: int) -> BrowseResults | StatusCodes:
        parts = media_id.split(":")
        if len(parts) < 2:
            return StatusCodes.BAD_REQUEST

        source = parts[1]
        path = [int(p) for p in parts[2:]] if len(parts) > 2 else []

        start_index = (page - 1) * 8
        result = await self._device.browse_netusb(source, path, index=start_index, size=8)
        if result is None:
            return StatusCodes.SERVER_ERROR

        list_items = result.get("list_info", [])
        menu_name = result.get("menu_name", source.replace("_", " ").title())
        max_line = result.get("max_line", 0)

        items = []
        for idx, item in enumerate(list_items):
            text = item.get("text", "").strip()
            if not text:
                continue
            attr = item.get("attribute", 0)
            can_browse = attr in (2, 3)
            can_play = attr != 2
            _LOG.debug("Browse item: text=%s, attribute=%s, can_browse=%s, can_play=%s",
                       text, attr, can_browse, can_play)

            absolute_idx = start_index + idx
            item_path = ":".join(str(p) for p in path + [absolute_idx])
            item_media_id = f"netusb:{source}:{item_path}"

            thumbnail = item.get("thumbnail", "") or item.get("logo", "") or None
            if thumbnail and thumbnail.startswith("/"):
                thumbnail = f"http://{self._device.address}{thumbnail}"

            items.append(BrowseMediaItem(
                media_id=item_media_id,
                title=text,
                media_type="netusb",
                media_class=MediaClass.DIRECTORY if can_browse else MediaClass.MUSIC,
                can_browse=can_browse,
                can_play=can_play,
                thumbnail=thumbnail,
            ))

        return BrowseResults(
            media=BrowseMediaItem(
                media_id=media_id,
                title=menu_name or source.replace("_", " ").title(),
                media_type="netusb",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                items=items,
            ),
            pagination=Pagination(page=page, limit=8, count=max_line),
        )

    def _browse_presets(self, page: int, limit: int) -> BrowseResults:
        all_presets = []
        for i in range(1, 41):
            all_presets.append(BrowseMediaItem(
                media_id=f"preset:{i}",
                title=self._device.preset_names[i - 1],
                media_type="preset",
                media_class=MediaClass.RADIO,
                can_browse=False,
                can_play=True,
            ))
        start = (page - 1) * limit
        page_items = all_presets[start: start + limit]
        return BrowseResults(
            media=BrowseMediaItem(
                media_id="presets",
                title="Presets / Favorites",
                media_type="presets",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                items=page_items,
            ),
            pagination=Pagination(page=page, limit=limit, count=len(all_presets)),
        )

    def _browse_sound_programs(self) -> BrowseResults:
        items = []
        for program_id in self._device.available_sound_programs:
            from uc_intg_musiccast.const import SOUND_MODE_MAPPING
            name = SOUND_MODE_MAPPING.get(program_id, program_id.replace("_", " ").title())
            items.append(BrowseMediaItem(
                media_id=f"program:{program_id}",
                title=name,
                media_type="sound_program",
                media_class=MediaClass.MUSIC,
                can_browse=False,
                can_play=True,
            ))
        return BrowseResults(
            media=BrowseMediaItem(
                media_id="sound_programs",
                title="Sound Programs",
                media_type="sound_programs",
                media_class=MediaClass.DIRECTORY,
                can_browse=True,
                items=items,
            ),
            pagination=Pagination(page=1, limit=len(items), count=len(items)),
        )

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
                    await self._device.play_pause()
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
                    await self._device.toggle_repeat()
                    await self._device._update_state()
                    self._device.push_update()
                case media_player.Commands.SHUFFLE:
                    await self._device.toggle_shuffle()
                    await self._device._update_state()
                    self._device.push_update()
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
                case media_player.Commands.PLAY_MEDIA:
                    if params and "media_id" in params:
                        media_id = params["media_id"]
                        media_type = params.get("media_type", "")
                        if media_type == "preset" and media_id.startswith("preset:"):
                            num = int(media_id.split(":")[1])
                            await self._device.recall_preset(num)
                        elif media_type == "source" and media_id.startswith("source:"):
                            input_id = media_id.split(":", 1)[1]
                            await self._device.set_input(input_id)
                        elif media_type == "sound_program" and media_id.startswith("program:"):
                            program_id = media_id.split(":", 1)[1]
                            await self._device.set_sound_program(program_id)
                        elif media_type == "netusb" and media_id.startswith("netusb:"):
                            parts = media_id.split(":")
                            source = parts[1]
                            indices = [int(p) for p in parts[2:]] if len(parts) > 2 else []
                            if not indices:
                                await self._device.set_input(source)
                            else:
                                path = indices[:-1]
                                item_index = indices[-1]
                                await self._device.play_netusb_item(source, path, item_index)
                        else:
                            return StatusCodes.BAD_REQUEST
                case _:
                    return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except Exception as err:
            _LOG.error("[%s] Command %s failed: %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR
