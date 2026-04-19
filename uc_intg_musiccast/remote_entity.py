"""
MusicCast remote entity with UI pages and button mappings.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_text
from ucapi_framework import RemoteEntity

from uc_intg_musiccast.config import MusicCastConfig
from uc_intg_musiccast.device import MusicCastDevice

_LOG = logging.getLogger(__name__)


def _build_simple_commands(device: MusicCastDevice) -> list[str]:
    commands = [
        "play", "pause", "stop", "next", "previous", "play_pause",
        "power_on", "power_off", "power_toggle",
        "volume_up", "volume_down", "mute_toggle",
        "repeat_off", "repeat_one", "repeat_all", "repeat_toggle",
        "shuffle_off", "shuffle_on", "shuffle_toggle",
        "thumbs_up", "thumbs_down",
    ]
    for source in device.available_inputs:
        commands.append(f"input_{source['id']}")
    for program in device.available_sound_programs:
        commands.append(f"sound_{program}")
    for i in range(1, 41):
        commands.append(f"preset_{i}")
    if device.scene_support:
        for i in range(1, 9):
            commands.append(f"scene_{i}")
    return commands


def _build_button_mapping() -> list:
    return [
        create_btn_mapping(Buttons.PLAY, short="play_pause"),
        create_btn_mapping(Buttons.PREV, short="previous"),
        create_btn_mapping(Buttons.NEXT, short="next"),
        create_btn_mapping(Buttons.VOLUME_UP, short="volume_up"),
        create_btn_mapping(Buttons.VOLUME_DOWN, short="volume_down"),
        create_btn_mapping(Buttons.MUTE, short="mute_toggle"),
        create_btn_mapping(Buttons.POWER, short="power_toggle"),
    ]


def _build_ui_pages(device: MusicCastDevice) -> list[UiPage]:
    pages = []

    main_page = UiPage("main", "Main Controls", grid=Size(4, 6), items=[
        create_ui_text("POWER", 0, 0, cmd="power_toggle"),
        create_ui_text("PREV", 1, 0, cmd="previous"),
        create_ui_text("PLAY", 2, 0, cmd="play_pause"),
        create_ui_text("NEXT", 3, 0, cmd="next"),
        create_ui_text("VOL-", 0, 1, cmd="volume_down"),
        create_ui_text("VOL+", 1, 1, cmd="volume_up"),
        create_ui_text("MUTE", 2, 1, cmd="mute_toggle"),
        create_ui_text("STOP", 3, 1, cmd="stop"),
        create_ui_text("REPEAT", 0, 2, cmd="repeat_toggle"),
        create_ui_text("SHUFFLE", 1, 2, cmd="shuffle_toggle"),
        create_ui_text("THUMBS+", 2, 2, cmd="thumbs_up"),
        create_ui_text("THUMBS-", 3, 2, cmd="thumbs_down"),
    ])
    pages.append(main_page)

    if device.available_inputs:
        items = []
        for i, source in enumerate(device.available_inputs[:16]):
            x, y = i % 4, i // 4
            if y >= 4:
                break
            label = source["name"][:8] if len(source["name"]) > 8 else source["name"]
            items.append(create_ui_text(label, x, y, cmd=f"input_{source['id']}"))
        pages.append(UiPage("sources", "Sources", grid=Size(4, 6), items=items))

    if device.available_sound_programs:
        popular = ["2ch_stereo", "all_ch_stereo", "straight", "standard",
                    "munich", "vienna", "sports", "music_video"]
        available_popular = [p for p in popular if p in device.available_sound_programs]
        others = [p for p in device.available_sound_programs if p not in popular]
        programs = (available_popular + others)[:16]

        display_names = {
            "2ch_stereo": "2CH", "all_ch_stereo": "ALLCH", "straight": "STRAIGHT",
            "standard": "STANDARD", "munich": "MUNICH", "vienna": "VIENNA",
            "sports": "SPORTS", "music_video": "MUSIC", "action_game": "ACTION",
            "drama": "DRAMA",
        }
        items = []
        for i, program in enumerate(programs):
            x, y = i % 4, i // 4
            if y >= 4:
                break
            label = display_names.get(program, program[:6].upper())
            items.append(create_ui_text(label, x, y, cmd=f"sound_{program}"))
        pages.append(UiPage("sound_programs", "Sound Programs", grid=Size(4, 6), items=items))

    for page_idx, start in enumerate([(1, 17), (17, 33), (33, 41)]):
        items = []
        for i, num in enumerate(range(start[0], start[1])):
            x, y = i % 4, i // 4
            if y >= 4:
                break
            items.append(create_ui_text(f"FAV{num}", x, y, cmd=f"preset_{num}"))
        suffix = "" if page_idx == 0 else str(page_idx + 1)
        page_name = f"Favorites {start[0]}-{start[1] - 1}"
        pages.append(UiPage(f"favorites{suffix}", page_name, grid=Size(4, 6), items=items))

    if device.scene_support:
        items = []
        for i in range(8):
            x, y = i % 4, i // 4
            items.append(create_ui_text(f"SCENE{i + 1}", x, y, cmd=f"scene_{i + 1}"))
        pages.append(UiPage("scenes", "Scenes", grid=Size(4, 6), items=items))

    return pages


class MusicCastRemote(RemoteEntity):
    """MusicCast remote entity."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"remote.{device_config.identifier}"
        super().__init__(
            entity_id,
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=_build_simple_commands(device),
            button_mapping=_build_button_mapping(),
            ui_pages=_build_ui_pages(device),
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({remote.Attributes.STATE: remote.States.UNAVAILABLE})
            return
        if self._device.power == "standby":
            self.update({remote.Attributes.STATE: remote.States.OFF})
        else:
            self.update({remote.Attributes.STATE: remote.States.ON})

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        try:
            if cmd_id == remote.Commands.ON:
                await self._device.set_power("on")
                return StatusCodes.OK
            if cmd_id == remote.Commands.OFF:
                await self._device.set_power("standby")
                return StatusCodes.OK
            if cmd_id == remote.Commands.TOGGLE:
                await self._device.set_power("toggle")
                return StatusCodes.OK

            if cmd_id == remote.Commands.SEND_CMD and params:
                command = params.get("command", "")
                if command:
                    return await self._execute_command(command)

            if cmd_id == remote.Commands.SEND_CMD_SEQUENCE and params:
                for command in params.get("sequence", []):
                    result = await self._execute_command(command)
                    if result != StatusCodes.OK:
                        return result
                return StatusCodes.OK

            return StatusCodes.NOT_IMPLEMENTED
        except Exception as err:
            _LOG.error("[%s] Command %s failed: %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _execute_command(self, command: str) -> StatusCodes:
        try:
            if command in ("play", "pause", "stop", "next", "previous", "play_pause"):
                await self._device.set_playback(command)
            elif command == "power_on":
                await self._device.set_power("on")
            elif command == "power_off":
                await self._device.set_power("standby")
            elif command == "power_toggle":
                await self._device.set_power("toggle")
            elif command == "volume_up":
                await self._device.volume_up()
            elif command == "volume_down":
                await self._device.volume_down()
            elif command == "mute_toggle":
                await self._device.set_mute(not self._device.muted)
            elif command in ("repeat_off", "repeat_one", "repeat_all"):
                await self._device.set_repeat(command.split("_", 1)[1])
            elif command == "repeat_toggle":
                await self._device.toggle_repeat()
            elif command in ("shuffle_off", "shuffle_on"):
                await self._device.set_shuffle(command.split("_", 1)[1])
            elif command == "shuffle_toggle":
                await self._device.toggle_shuffle()
            elif command.startswith("input_"):
                input_id = command[6:]
                if any(src["id"] == input_id for src in self._device.available_inputs):
                    await self._device.set_input(input_id)
                else:
                    return StatusCodes.BAD_REQUEST
            elif command.startswith("sound_"):
                program_id = command[6:]
                if program_id in self._device.available_sound_programs:
                    await self._device.set_sound_program(program_id)
                else:
                    return StatusCodes.BAD_REQUEST
            elif command.startswith("preset_"):
                num = int(command[7:])
                if 1 <= num <= 40:
                    await self._device.recall_preset(num)
                else:
                    return StatusCodes.BAD_REQUEST
            elif command.startswith("scene_"):
                num = int(command[6:])
                if 1 <= num <= 8:
                    await self._device.recall_scene(num)
                else:
                    return StatusCodes.BAD_REQUEST
            elif command == "thumbs_up":
                await self._device.manage_play("thumbs_up")
            elif command == "thumbs_down":
                await self._device.manage_play("thumbs_down")
            else:
                return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except ValueError:
            return StatusCodes.BAD_REQUEST
