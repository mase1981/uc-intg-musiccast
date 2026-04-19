"""
MusicCast sensor entities.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi import sensor
from ucapi_framework import SensorEntity

from uc_intg_musiccast.config import MusicCastConfig
from uc_intg_musiccast.device import MusicCastDevice

_LOG = logging.getLogger(__name__)


class InputSourceSensor(SensorEntity):
    """Displays the current input source."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.input_source"
        super().__init__(
            entity_id,
            f"{device_config.name} Input Source",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._device.input_source_name or "Unknown",
        })


class SoundModeSensor(SensorEntity):
    """Displays the current sound mode/program."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.sound_mode"
        super().__init__(
            entity_id,
            f"{device_config.name} Sound Mode",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._device.sound_program_name or "Unknown",
        })


class PlaybackSensor(SensorEntity):
    """Displays the current playback state."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.playback"
        super().__init__(
            entity_id,
            f"{device_config.name} Playback",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return

        if self._device.power == "standby":
            value = "Standby"
        elif self._device.playback == "play":
            value = self._device.track or "Playing"
        elif self._device.playback == "pause":
            value = "Paused"
        else:
            value = "Idle"

        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: value,
        })


class ModelSensor(SensorEntity):
    """Displays the device model name."""

    def __init__(self, device_config: MusicCastConfig, device: MusicCastDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.model"
        super().__init__(
            entity_id,
            f"{device_config.name} Model",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state == "UNAVAILABLE":
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._device.model_name or "Unknown",
        })


def create_sensors(config: MusicCastConfig, device: MusicCastDevice) -> list:
    return [
        InputSourceSensor(config, device),
        SoundModeSensor(config, device),
        PlaybackSensor(config, device),
        ModelSensor(config, device),
    ]
