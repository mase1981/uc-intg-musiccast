"""
MusicCast device implementation using PollingDevice.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any

from ucapi_framework import DeviceEvents, PollingDevice

from uc_intg_musiccast.client import YamahaMusicCastClient
from uc_intg_musiccast.config import MusicCastConfig
from uc_intg_musiccast.const import (
    MAX_CONSECUTIVE_FAILURES,
    POLL_INTERVAL,
    POLL_INTERVAL_STANDBY,
    RECONNECT_INTERVAL,
    SOUND_MODE_MAPPING,
)

_LOG = logging.getLogger(__name__)


class MusicCastDevice(PollingDevice):
    """Yamaha MusicCast device."""

    def __init__(self, device_config: MusicCastConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=POLL_INTERVAL, **kwargs)
        self._device_config = device_config
        self._client: YamahaMusicCastClient | None = None
        self._state: str = "UNAVAILABLE"
        self._consecutive_failures: int = 0
        self._reconnect_poll_count: int = 0

        self._power: str = "standby"
        self._volume: int = 0
        self._max_volume: int = 161
        self._muted: bool = False
        self._input_source: str = ""
        self._input_source_name: str = ""
        self._sound_program: str = ""
        self._sound_program_name: str = ""
        self._playback: str = "stop"
        self._artist: str = ""
        self._album: str = ""
        self._track: str = ""
        self._albumart_url: str = ""
        self._play_time: int = 0
        self._total_time: int = 0
        self._repeat: str = "off"
        self._shuffle: bool = False

        self._available_inputs: list[dict] = []
        self._available_sound_programs: list[str] = []
        self._scene_support: bool = False
        self._model_name: str = "MusicCast"
        self._preset_info: dict[int, str] = {}
        self._current_preset_name: str = ""

    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.address

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self._device_config.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def client(self) -> YamahaMusicCastClient | None:
        return self._client

    @property
    def power(self) -> str:
        return self._power

    @property
    def volume_percent(self) -> int:
        if self._max_volume <= 0:
            return 0
        return min(100, max(0, int((self._volume / self._max_volume) * 100)))

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def input_source(self) -> str:
        return self._input_source

    @property
    def input_source_name(self) -> str:
        return self._input_source_name

    @property
    def sound_program(self) -> str:
        return self._sound_program

    @property
    def sound_program_name(self) -> str:
        return self._sound_program_name

    @property
    def playback(self) -> str:
        return self._playback

    @property
    def artist(self) -> str:
        return self._artist

    @property
    def album(self) -> str:
        return self._album

    @property
    def track(self) -> str:
        return self._track

    @property
    def albumart_url(self) -> str:
        return self._albumart_url

    @property
    def play_time(self) -> int:
        return self._play_time

    @property
    def total_time(self) -> int:
        return self._total_time

    @property
    def repeat(self) -> str:
        return self._repeat

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def available_inputs(self) -> list[dict]:
        return self._available_inputs

    @property
    def available_sound_programs(self) -> list[str]:
        return self._available_sound_programs

    @property
    def source_names(self) -> list[str]:
        return [src["name"] for src in self._available_inputs]

    @property
    def sound_mode_names(self) -> list[str]:
        return [
            SOUND_MODE_MAPPING.get(p, p.replace("_", " ").title())
            for p in self._available_sound_programs
        ]

    @property
    def scene_support(self) -> bool:
        return self._scene_support

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def preset_names(self) -> list[str]:
        names = []
        for i in range(1, 41):
            name = self._preset_info.get(i, "")
            if name:
                names.append(name)
            else:
                names.append(f"Preset {i}")
        return names

    @property
    def current_preset_name(self) -> str:
        return self._current_preset_name

    def get_preset_num_by_name(self, name: str) -> int | None:
        for num, preset_name in self._preset_info.items():
            if preset_name == name:
                return num
        if name.startswith("Preset "):
            try:
                return int(name.split(" ")[1])
            except (ValueError, IndexError):
                pass
        return None

    async def establish_connection(self) -> YamahaMusicCastClient:
        self._client = YamahaMusicCastClient(
            self._device_config.address,
            port=self._device_config.port,
            use_ssl=self._device_config.use_ssl,
        )

        device_info = await self._client.get_device_info()
        self._model_name = device_info.model_name
        _LOG.info("[%s] Connected to %s", self.log_id, device_info.model_name)

        try:
            self._available_inputs = await self._client.get_available_inputs()
            self._available_sound_programs = await self._client.get_available_sound_programs()
            self._scene_support = await self._client.get_scene_support()
            _LOG.info(
                "[%s] %d inputs, %d sound programs, scenes: %s",
                self.log_id,
                len(self._available_inputs),
                len(self._available_sound_programs),
                self._scene_support,
            )
        except Exception as err:
            _LOG.warning("[%s] Could not fetch capabilities: %s", self.log_id, err)

        try:
            preset_data = await self._client.get_preset_info()
            self._preset_info = self._parse_preset_info(preset_data)
            named = sum(1 for n in self._preset_info.values() if n)
            _LOG.info("[%s] %d named presets found", self.log_id, named)
        except Exception as err:
            _LOG.warning("[%s] Could not fetch presets: %s", self.log_id, err)

        try:
            await self._update_state()
        except Exception:
            _LOG.warning("[%s] Initial state query failed, using defaults", self.log_id)

        self._state = "ON"
        self._consecutive_failures = 0
        return self._client

    async def poll_device(self) -> None:
        if self._state == "UNAVAILABLE":
            self._reconnect_poll_count += 1
            polls_needed = RECONNECT_INTERVAL // max(POLL_INTERVAL, 1)
            if self._reconnect_poll_count >= max(polls_needed, 3):
                self._reconnect_poll_count = 0
                await self._try_reconnect()
            return

        if not self._client:
            return

        try:
            await self._update_state()
            self._consecutive_failures = 0

            if self._power == "standby":
                self._poll_interval = POLL_INTERVAL_STANDBY
            else:
                self._poll_interval = POLL_INTERVAL

            self.push_update()
        except Exception as err:
            self._consecutive_failures += 1
            _LOG.debug(
                "[%s] Poll error (%d/%d): %s",
                self.log_id,
                self._consecutive_failures,
                MAX_CONSECUTIVE_FAILURES,
                err,
            )
            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                _LOG.warning("[%s] Max failures reached, marking unavailable", self.log_id)
                self._state = "UNAVAILABLE"
                self._power = "standby"
                self._reconnect_poll_count = 0
                self.push_update()
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    async def _update_state(self) -> None:
        status = await self._client.get_status()
        if status is None:
            raise ConnectionError("Failed to get device status")

        self._power = status.power
        self._volume = status.volume
        self._max_volume = status.max_volume
        self._muted = status.mute
        self._input_source = status.input
        self._input_source_name = next(
            (src["name"] for src in self._available_inputs if src["id"] == status.input),
            status.input_text or status.input.replace("_", " ").title(),
        )
        self._sound_program = status.sound_program
        self._sound_program_name = SOUND_MODE_MAPPING.get(
            status.sound_program, status.sound_program.replace("_", " ").title()
        )

        play_info = await self._client.get_play_info()
        self._playback = play_info.playback
        self._repeat = play_info.repeat
        self._shuffle = play_info.shuffle == "on"

        if play_info.playback in ("play", "pause"):
            self._artist = play_info.artist
            self._album = play_info.album
            self._track = play_info.track
            self._albumart_url = play_info.albumart_url
            self._play_time = play_info.play_time
            self._total_time = play_info.total_time
        else:
            self._artist = ""
            self._album = ""
            self._track = ""
            self._albumart_url = ""
            self._play_time = 0
            self._total_time = 0

    async def _try_reconnect(self) -> bool:
        _LOG.info("[%s] Attempting reconnection...", self.log_id)
        try:
            await self.establish_connection()
            _LOG.info("[%s] Reconnected successfully", self.log_id)
            self.push_update()
            self.events.emit(DeviceEvents.CONNECTED, self.identifier)
            return True
        except Exception as err:
            _LOG.debug("[%s] Reconnection failed: %s", self.log_id, err)
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        self._state = "UNAVAILABLE"
        await super().disconnect()

    async def set_power(self, power: str) -> None:
        await self._client.set_power(power=power)

    async def set_volume(self, volume: int) -> None:
        device_vol = min(self._max_volume, max(0, int((volume / 100) * self._max_volume)))
        await self._client.set_volume(volume=device_vol)

    async def volume_up(self) -> None:
        await self._client.set_volume(direction="up", step=1)

    async def volume_down(self) -> None:
        await self._client.set_volume(direction="down", step=1)

    async def set_mute(self, enable: bool) -> None:
        await self._client.set_mute(enable=enable)

    async def set_input(self, input_id: str) -> None:
        await self._client.set_input(input_source=input_id)

    async def set_sound_program(self, program_id: str) -> None:
        await self._client.set_sound_program(program=program_id)

    async def set_playback(self, playback: str) -> None:
        await self._client.set_playback(playback)

    async def play_pause(self) -> None:
        if self._playback == "play":
            await self._client.set_playback("pause")
        else:
            await self._client.set_playback("play")

    async def set_repeat(self, repeat: str) -> None:
        await self._client.set_repeat(repeat)

    async def set_shuffle(self, shuffle: str) -> None:
        await self._client.set_shuffle(shuffle)

    async def toggle_repeat(self) -> None:
        await self._client.toggle_repeat()

    async def toggle_shuffle(self) -> None:
        await self._client.toggle_shuffle()

    async def recall_preset(self, num: int) -> None:
        await self._client.recall_preset(num=num)
        name = self._preset_info.get(num, f"Preset {num}")
        self._current_preset_name = name

    async def recall_scene(self, num: int) -> None:
        await self._client.recall_scene(num=num)

    async def manage_play(self, action_type: str) -> None:
        await self._client.manage_play(action_type)

    async def _navigate_to_root(self, source: str) -> dict:
        result = await self._client.get_list_info(input_source=source, index=0, size=8)
        menu_layer = result.get("menu_layer", 0)
        while menu_layer > 0:
            await self._client.set_list_control(control_type="return")
            await asyncio.sleep(0.3)
            result = await self._client.get_list_info(input_source=source, index=0, size=8)
            new_layer = result.get("menu_layer", 0)
            if new_layer >= menu_layer:
                break
            menu_layer = new_layer
        return result

    async def browse_netusb(self, source: str, path: list[int], index: int = 0, size: int = 8) -> dict | None:
        try:
            result = await self._navigate_to_root(source)
            if not path:
                if index != 0 or size != 8:
                    result = await self._client.get_list_info(input_source=source, index=index, size=size)
                return result

            for step in path:
                await self._client.set_list_control(control_type="select", index=step)
                await asyncio.sleep(0.5)
                result = await self._client.get_list_info(input_source=source, index=0, size=8)

            if index != 0 or size != 8:
                result = await self._client.get_list_info(input_source=source, index=index, size=size)

            return result
        except Exception as err:
            _LOG.error("[%s] Netusb browse failed: %s", self.log_id, err)
            return None

    async def play_netusb_item(self, source: str, path: list[int], item_index: int) -> None:
        await self._navigate_to_root(source)
        for step in path:
            await self._client.set_list_control(control_type="select", index=step)
            await asyncio.sleep(0.5)
            await self._client.get_list_info(input_source=source, index=0, size=8)
        await self._client.set_list_control(control_type="play", index=item_index)

    async def play_netusb_folder(self, source: str, path: list[int]) -> None:
        await self._navigate_to_root(source)
        for step in path:
            await self._client.set_list_control(control_type="select", index=step)
            await asyncio.sleep(0.5)
            await self._client.get_list_info(input_source=source, index=0, size=8)
        await self._client.set_list_control(control_type="play", index=0)

    @staticmethod
    def _parse_preset_info(data: dict) -> dict[int, str]:
        presets: dict[int, str] = {}
        preset_info = data.get("preset_info", [])
        for band_list in preset_info:
            if not isinstance(band_list, list):
                continue
            for item in band_list:
                if not isinstance(item, dict):
                    continue
                text = item.get("text", "").strip()
                num = item.get("number", 0)
                if num and text:
                    presets[num] = text
        if not presets:
            for key, value in data.items():
                if key == "response_code":
                    continue
                if isinstance(value, list):
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            text = item.get("text", "").strip()
                            if text:
                                presets[idx + 1] = text
        return presets

    def get_input_id_by_name(self, name: str) -> str | None:
        return next(
            (src["id"] for src in self._available_inputs if src["name"] == name),
            None,
        )

    def get_program_id_by_name(self, name: str) -> str | None:
        from uc_intg_musiccast.const import SOUND_MODE_REVERSE
        program_id = SOUND_MODE_REVERSE.get(name)
        if program_id and program_id in self._available_sound_programs:
            return program_id
        return next(
            (p for p in self._available_sound_programs if p.replace("_", " ").title() == name),
            None,
        )
