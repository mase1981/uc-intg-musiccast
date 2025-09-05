"""
Yamaha MusicCast Remote Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import ucapi
from ucapi.remote import Attributes, Features, Remote, States

from uc_intg_musiccast.client import YamahaMusicCastClient

_LOG = logging.getLogger(__name__)

class MusicCastRemote(Remote):
    """Remote entity for Yamaha MusicCast devices."""

    def __init__(self, device_id: str, device_name: str):
        """Initialize the remote entity."""
        features = [Features.SEND_CMD]
        attributes = {Attributes.STATE: States.ON}
        simple_commands, ui_pages = self._build_ui()

        super().__init__(
            identifier=f"{device_id}_remote",
            name=f"{device_name} Remote",
            features=features,
            attributes=attributes,
            simple_commands=simple_commands,
            ui_pages=ui_pages,
            cmd_handler=self._handle_command,
        )

        self._client: Optional[YamahaMusicCastClient] = None
        self._zone: str = "main"
        self._capabilities_initialized = False
        self._integration_api = None

    def set_client(self, client):
        """Set the MusicCast API client."""
        self._client = client

    async def initialize_capabilities(self):
        """Initialize remote capabilities."""
        if self._capabilities_initialized:
            return
        _LOG.info("Initializing MusicCast remote capabilities")
        self.attributes[Attributes.STATE] = States.ON
        self._force_integration_update()
        self._capabilities_initialized = True

    async def update_attributes(self):
        """Update remote attributes."""
        if not self._capabilities_initialized:
            await self.initialize_capabilities()
        self.attributes[Attributes.STATE] = States.ON
        self._force_integration_update()

    def _force_integration_update(self):
        """Force update to integration API."""
        if self._integration_api:
            try:
                self._integration_api.configured_entities.update_attributes(
                    self.id, self.attributes
                )
            except Exception as e:
                _LOG.debug("Could not update integration API: %s", e)

    def _build_ui(self) -> (List[str], List[Dict[str, Any]]):
        """Builds the command list and UI pages."""
        commands = [
            'play', 'pause', 'stop', 'next', 'previous', 'volume_up', 'volume_down',
            'mute_toggle', 'power_on', 'power_off', 'power_toggle', 'input_hdmi',
            'input_analog', 'input_bluetooth', 'input_spotify', 'sound_stereo',
            'sound_standard', 'sound_surround', 'sound_movie', 'sound_music',
            'repeat_off', 'repeat_one', 'repeat_all', 'shuffle_off', 'shuffle_on',
            'play_pause'
        ]

        pages = [
            {
                'page_id': 'main',
                'name': 'Main Controls',
                'grid': {'width': 4, 'height': 6},
                'items': [
                    {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'PREV', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'previous'}}},
                    {'type': 'text', 'location': {'x': 2, 'y': 0}, 'text': 'PLAY/PAUSE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'play_pause'}}},
                    {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'NEXT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'next'}}},
                    {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'VOL-', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_down'}}},
                    {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'VOL+', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_up'}}},
                    {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'MUTE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'mute_toggle'}}},
                    {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'STOP', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'stop'}}},
                    {'type': 'text', 'location': {'x': 0, 'y': 2}, 'text': 'POWER', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'power_toggle'}}},
                ]
            },
            {
                'page_id': 'sources',
                'name': 'Sources',
                'grid': {'width': 4, 'height': 6},
                'items': [
                    {'type': 'text', 'location': {'x': 0, 'y': 0}, 'text': 'Spotify', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'input_spotify'}}},
                    {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'Bluetooth', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'input_bluetooth'}}},
                    {'type': 'text', 'location': {'x': 2, 'y': 0}, 'text': 'HDMI', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'input_hdmi'}}},
                    {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'Analog', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'input_analog'}}},
                ]
            }
        ]
        return commands, pages

    async def _handle_command(self, entity, cmd_id: str, params: dict = None) -> ucapi.StatusCodes:
        """Handle remote commands."""
        if not self._client:
            return ucapi.StatusCodes.SERVER_ERROR

        try:
            command = params.get('command') if params else None
            if cmd_id == "send_cmd" and command:
                _LOG.info(f"Executing remote command: {command}")
                
                # Playback commands
                if command == 'play_pause':
                    await self._client.set_playback('play_pause')
                elif command == 'play':
                    await self._client.set_playback('play')
                elif command == 'pause':
                    await self._client.set_playback('pause')
                elif command == 'stop':
                    await self._client.set_playback('stop')
                elif command == 'next':
                    await self._client.set_playback('next')
                elif command == 'previous':
                    await self._client.set_playback('previous')
                # Power commands
                elif command == 'power_on':
                    await self._client.set_power(self._zone, 'on')
                elif command == 'power_off':
                    await self._client.set_power(self._zone, 'standby')
                elif command == 'power_toggle':
                    await self._client.set_power(self._zone, 'toggle')
                # Volume commands
                elif command == 'volume_up':
                    await self._client.set_volume(self._zone, step=1)
                elif command == 'volume_down':
                    await self._client.set_volume(self._zone, step=-1)
                elif command == 'mute_toggle':
                    current_mute = self._get_current_mute_state()
                    await self._client.set_mute(self._zone, enable=not current_mute)
                # Input commands
                elif command == 'input_hdmi':
                    await self._client.set_input(self._zone, 'hdmi')
                elif command == 'input_analog':
                    await self._client.set_input(self._zone, 'analog')
                elif command == 'input_bluetooth':
                    await self._client.set_input(self._zone, 'bluetooth')
                elif command == 'input_spotify':
                    await self._client.set_input(self._zone, 'spotify')
                # Repeat commands
                elif command == 'repeat_off':
                    await self._client.set_repeat('off')
                elif command == 'repeat_one':
                    await self._client.set_repeat('one')
                elif command == 'repeat_all':
                    await self._client.set_repeat('all')
                # Shuffle commands
                elif command == 'shuffle_off':
                    await self._client.set_shuffle('off')
                elif command == 'shuffle_on':
                    await self._client.set_shuffle('on')
                else:
                    _LOG.warning(f"Unhandled remote command: {command}")
                    return ucapi.StatusCodes.NOT_IMPLEMENTED
                
                asyncio.create_task(self._deferred_update())
                return ucapi.StatusCodes.OK
            else:
                return ucapi.StatusCodes.BAD_REQUEST

        except Exception as e:
            _LOG.error(f"Error executing command {params}: {e}")
            return ucapi.StatusCodes.SERVER_ERROR

    def _get_current_mute_state(self) -> bool:
        """Helper to safely get mute state from parent media player."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                mp_entity = self._integration_api.configured_entities.get(
                    self.id.replace('_remote', '_media_player')
                )
                if mp_entity:
                    return mp_entity.attributes.get('muted', False)
        except Exception as e:
            _LOG.debug(f"Could not get mute state: {e}")
        return False

    async def _deferred_update(self):
        """Force a state poll after a command."""
        await asyncio.sleep(0.5)
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                mp_entity = self._integration_api.configured_entities.get(
                    self.id.replace('_remote', '_media_player')
                )
                if mp_entity and hasattr(mp_entity, 'update_attributes'):
                    await mp_entity.update_attributes()
        except Exception as e:
            _LOG.error(f"Could not trigger deferred update for media player: {e}")