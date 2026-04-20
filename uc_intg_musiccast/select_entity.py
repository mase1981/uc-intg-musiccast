"""
MusicCast select entities for input source and sound program.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.select import Attributes, States, Commands
from ucapi_framework import SelectEntity

from uc_intg_musiccast.config import MusicCastConfig
from uc_intg_musiccast.device import MusicCastDevice

_LOG = logging.getLogger(__name__)


class InputSelect(SelectEntity):
    """Select entity for input source selection."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.input"
        super().__init__(
            entity_id,
            f"{device_config.name} Input",
            {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.OPTIONS: [],
                Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return
        self.update({
            Attributes.STATE: States.ON,
            Attributes.OPTIONS: self._device.source_names,
            Attributes.CURRENT_OPTION: self._device.input_source_name,
        })

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        try:
            if cmd_id == Commands.SELECT_OPTION and params and "option" in params:
                source_name = params["option"]
                source_id = self._device.get_input_id_by_name(source_name)
                if source_id:
                    await self._device.set_input(source_id)
                    return StatusCodes.OK
                return StatusCodes.BAD_REQUEST
            return StatusCodes.NOT_IMPLEMENTED
        except Exception as err:
            _LOG.error("[%s] Select command failed: %s", entity.id, err)
            return StatusCodes.SERVER_ERROR


class SoundProgramSelect(SelectEntity):
    """Select entity for sound program selection."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.sound_program"
        super().__init__(
            entity_id,
            f"{device_config.name} Sound Program",
            {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.OPTIONS: [],
                Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return
        self.update({
            Attributes.STATE: States.ON,
            Attributes.OPTIONS: self._device.sound_mode_names,
            Attributes.CURRENT_OPTION: self._device.sound_program_name,
        })

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        try:
            if cmd_id == Commands.SELECT_OPTION and params and "option" in params:
                program_name = params["option"]
                program_id = self._device.get_program_id_by_name(program_name)
                if program_id:
                    await self._device.set_sound_program(program_id)
                    return StatusCodes.OK
                return StatusCodes.BAD_REQUEST
            return StatusCodes.NOT_IMPLEMENTED
        except Exception as err:
            _LOG.error("[%s] Select command failed: %s", entity.id, err)
            return StatusCodes.SERVER_ERROR


class PresetSelect(SelectEntity):
    """Select entity for preset/favorites recall."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.preset"
        super().__init__(
            entity_id,
            f"{device_config.name} Preset",
            {
                Attributes.STATE: States.UNAVAILABLE,
                Attributes.OPTIONS: [],
                Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({Attributes.STATE: States.UNAVAILABLE})
            return
        self.update({
            Attributes.STATE: States.ON,
            Attributes.OPTIONS: self._device.preset_names,
            Attributes.CURRENT_OPTION: self._device.current_preset_name,
        })

    async def _handle_command(
        self, entity: Any, cmd_id: str, params: dict[str, Any] | None
    ) -> StatusCodes:
        try:
            if cmd_id == Commands.SELECT_OPTION and params and "option" in params:
                option = params["option"]
                preset_num = self._device.get_preset_num_by_name(option)
                if preset_num and 1 <= preset_num <= 40:
                    await self._device.recall_preset(preset_num)
                    return StatusCodes.OK
                return StatusCodes.BAD_REQUEST
            return StatusCodes.NOT_IMPLEMENTED
        except Exception as err:
            _LOG.error("[%s] Select command failed: %s", entity.id, err)
            return StatusCodes.SERVER_ERROR


def create_selects(config: MusicCastConfig, device: MusicCastDevice) -> list:
    return [
        InputSelect(config, device),
        SoundProgramSelect(config, device),
        PresetSelect(config, device),
    ]
