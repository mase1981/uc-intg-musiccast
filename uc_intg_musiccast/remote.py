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
    """Remote entity for Yamaha MusicCast devices with multi-device support."""

    def __init__(self, entity_id: str, device_name: str):
        """Initialize the remote entity with custom entity ID for multi-device support."""
        features = [Features.SEND_CMD]
        attributes = {Attributes.STATE: States.ON}
        simple_commands, ui_pages = self._build_ui()

        super().__init__(
            identifier=entity_id,  # Use provided entity_id for multi-device support
            name=f"{device_name} Remote",  # Each device gets its own name
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
        self._available_sources = []
        self._available_sound_programs = []

    def set_client(self, client):
        """Set the MusicCast API client."""
        self._client = client

    async def initialize_capabilities(self):
        """Initialize remote capabilities from real device."""
        if self._capabilities_initialized:
            return
            
        _LOG.info("Initializing MusicCast remote capabilities for %s", self.id)
        
        if self._client:
            try:
                # Get device capabilities
                available_inputs = await self._client.get_available_inputs(self._zone)
                self._available_sources = available_inputs
                
                sound_programs = await self._client.get_available_sound_programs(self._zone)
                self._available_sound_programs = sound_programs
                
                # Rebuild UI with actual device capabilities
                simple_commands, ui_pages = self._build_enhanced_ui()
                
                # Update the entity options
                if hasattr(self, 'options') and self.options:
                    self.options["simple_commands"] = simple_commands
                    self.options["user_interface"] = {"pages": ui_pages}
                
                _LOG.info(f"Remote initialized with {len(self._available_sources)} sources and {len(sound_programs)} sound programs for {self.id}")
                
            except Exception as e:
                _LOG.error(f"Failed to initialize remote capabilities for {self.id}: {e}")
        
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
                _LOG.debug("Could not update integration API for %s: %s", self.id, e)

    def _build_ui(self) -> (List[str], List[Dict[str, Any]]):
        """Build basic UI for initial setup."""
        commands = [
            'play', 'pause', 'stop', 'next', 'previous', 'volume_up', 'volume_down',
            'mute_toggle', 'power_on', 'power_off', 'power_toggle', 'play_pause'
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
            }
        ]
        return commands, pages

    def _build_enhanced_ui(self) -> (List[str], List[Dict[str, Any]]):
        """Build enhanced UI based on real device capabilities."""
        # Build comprehensive command list
        commands = [
            # Basic playback
            'play', 'pause', 'stop', 'next', 'previous', 'play_pause',
            # Power
            'power_on', 'power_off', 'power_toggle',
            # Volume
            'volume_up', 'volume_down', 'mute_toggle',
            # Repeat and shuffle
            'repeat_off', 'repeat_one', 'repeat_all', 'shuffle_off', 'shuffle_on'
        ]

        # Add input commands for available sources
        for source in self._available_sources:
            commands.append(f"input_{source['id']}")

        # Add sound program commands
        for program in self._available_sound_programs:
            commands.append(f"sound_{program}")

        # Build enhanced UI pages
        pages = []

        # Main control page
        pages.append({
            'page_id': 'main',
            'name': 'Main Controls',
            'grid': {'width': 4, 'height': 6},
            'items': [
                {'type': 'text', 'location': {'x': 0, 'y': 0}, 'text': 'POWER', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'power_toggle'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'PREV', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'previous'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 0}, 'text': 'PLAY/PAUSE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'play_pause'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'NEXT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'next'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'VOL-', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_down'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'VOL+', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'volume_up'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'MUTE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'mute_toggle'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'STOP', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'stop'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 2}, 'text': 'REPEAT', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'repeat_toggle'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': 'SHUFFLE', 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'shuffle_toggle'}}},
            ]
        })

        # Sources page with actual device inputs
        if self._available_sources:
            source_items = []
            x, y = 0, 0
            for i, source in enumerate(self._available_sources[:16]):  # Max 16 sources on 4x4 grid
                if x >= 4:
                    x = 0
                    y += 1
                    if y >= 4:  # Max 4 rows
                        break
                
                # Truncate long names for UI
                display_name = source['name'][:8] if len(source['name']) > 8 else source['name']
                
                source_items.append({
                    'type': 'text',
                    'location': {'x': x, 'y': y},
                    'text': display_name,
                    'command': {'cmd_id': 'send_cmd', 'params': {'command': f"input_{source['id']}"}}
                })
                x += 1

            pages.append({
                'page_id': 'sources',
                'name': 'Sources',
                'grid': {'width': 4, 'height': 6},
                'items': source_items
            })

        # Sound programs page
        if self._available_sound_programs:
            sound_items = []
            x, y = 0, 0
            
            # Popular sound programs for main page
            popular_programs = ['2ch_stereo', 'all_ch_stereo', 'straight', 'standard', 
                              'munich', 'vienna', 'sports', 'music_video']
            
            available_popular = [p for p in popular_programs if p in self._available_sound_programs]
            other_programs = [p for p in self._available_sound_programs if p not in popular_programs]
            
            # Combine popular first, then others
            programs_to_show = (available_popular + other_programs)[:16]
            
            for program in programs_to_show:
                if x >= 4:
                    x = 0
                    y += 1
                    if y >= 4:
                        break
                
                # Create friendly display names
                display_names = {
                    '2ch_stereo': '2CH',
                    'all_ch_stereo': 'ALLCH',
                    'straight': 'STRAIGHT',
                    'standard': 'STANDARD',
                    'munich': 'MUNICH',
                    'vienna': 'VIENNA',
                    'sports': 'SPORTS',
                    'music_video': 'MUSIC',
                    'action_game': 'ACTION',
                    'drama': 'DRAMA'
                }
                
                display_name = display_names.get(program, program[:6].upper())
                
                sound_items.append({
                    'type': 'text',
                    'location': {'x': x, 'y': y},
                    'text': display_name,
                    'command': {'cmd_id': 'send_cmd', 'params': {'command': f"sound_{program}"}}
                })
                x += 1

            pages.append({
                'page_id': 'sound_programs',
                'name': 'Sound Programs',
                'grid': {'width': 4, 'height': 6},
                'items': sound_items
            })

        return commands, pages

    async def _handle_command(self, entity, cmd_id: str, params: dict = None) -> ucapi.StatusCodes:
        """Handle remote commands."""
        if not self._client:
            return ucapi.StatusCodes.SERVER_ERROR

        try:
            command = params.get('command') if params else None
            if cmd_id == "send_cmd" and command:
                _LOG.info(f"Executing remote command for {self.id}: {command}")
                
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
                # Repeat/Shuffle commands
                elif command == 'repeat_off':
                    await self._client.set_repeat('off')
                elif command == 'repeat_one':
                    await self._client.set_repeat('one')
                elif command == 'repeat_all':
                    await self._client.set_repeat('all')
                elif command == 'repeat_toggle':
                    # Cycle through repeat modes
                    current_repeat = self._get_current_repeat_state()
                    next_repeat = {'off': 'all', 'all': 'one', 'one': 'off'}.get(current_repeat, 'off')
                    await self._client.set_repeat(next_repeat)
                elif command == 'shuffle_off':
                    await self._client.set_shuffle('off')
                elif command == 'shuffle_on':
                    await self._client.set_shuffle('on')
                elif command == 'shuffle_toggle':
                    current_shuffle = self._get_current_shuffle_state()
                    await self._client.set_shuffle('off' if current_shuffle else 'on')
                # Input commands (dynamic based on device capabilities)
                elif command.startswith('input_'):
                    input_id = command[6:]  # Remove 'input_' prefix
                    if any(src['id'] == input_id for src in self._available_sources):
                        await self._client.set_input(self._zone, input_id)
                    else:
                        _LOG.warning(f"Input not available: {input_id} for {self.id}")
                        return ucapi.StatusCodes.BAD_REQUEST
                # Sound program commands (dynamic based on device capabilities)
                elif command.startswith('sound_'):
                    program_id = command[6:]  # Remove 'sound_' prefix
                    if program_id in self._available_sound_programs:
                        await self._client.set_sound_program(self._zone, program_id)
                    else:
                        _LOG.warning(f"Sound program not available: {program_id} for {self.id}")
                        return ucapi.StatusCodes.BAD_REQUEST
                else:
                    _LOG.warning(f"Unhandled remote command: {command} for {self.id}")
                    return ucapi.StatusCodes.NOT_IMPLEMENTED
                
                asyncio.create_task(self._deferred_update())
                return ucapi.StatusCodes.OK
            else:
                return ucapi.StatusCodes.BAD_REQUEST

        except Exception as e:
            _LOG.error(f"Error executing command {params} for {self.id}: {e}")
            return ucapi.StatusCodes.SERVER_ERROR

    def _get_current_mute_state(self) -> bool:
        """Helper to safely get mute state from parent media player."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                # Find corresponding media player entity
                mp_entity_id = self.id.replace('_remote', '_media_player')
                mp_entity = None
                for entity in self._integration_api.configured_entities._entities:
                    if entity.id == mp_entity_id:
                        mp_entity = entity
                        break
                if mp_entity:
                    return mp_entity.attributes.get('muted', False)
        except Exception as e:
            _LOG.debug(f"Could not get mute state for {self.id}: {e}")
        return False

    def _get_current_repeat_state(self) -> str:
        """Helper to get current repeat state."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                # Find corresponding media player entity
                mp_entity_id = self.id.replace('_remote', '_media_player')
                mp_entity = None
                for entity in self._integration_api.configured_entities._entities:
                    if entity.id == mp_entity_id:
                        mp_entity = entity
                        break
                if mp_entity:
                    return mp_entity.attributes.get('repeat', 'off')
        except Exception as e:
            _LOG.debug(f"Could not get repeat state for {self.id}: {e}")
        return 'off'

    def _get_current_shuffle_state(self) -> bool:
        """Helper to get current shuffle state."""
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                # Find corresponding media player entity
                mp_entity_id = self.id.replace('_remote', '_media_player')
                mp_entity = None
                for entity in self._integration_api.configured_entities._entities:
                    if entity.id == mp_entity_id:
                        mp_entity = entity
                        break
                if mp_entity:
                    return mp_entity.attributes.get('shuffle', False)
        except Exception as e:
            _LOG.debug(f"Could not get shuffle state for {self.id}: {e}")
        return False

    async def _deferred_update(self):
        """Force a state poll after a command."""
        await asyncio.sleep(0.5)
        try:
            if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
                # Find corresponding media player entity
                mp_entity_id = self.id.replace('_remote', '_media_player')
                mp_entity = None
                for entity in self._integration_api.configured_entities._entities:
                    if entity.id == mp_entity_id:
                        mp_entity = entity
                        break
                if mp_entity and hasattr(mp_entity, 'update_attributes'):
                    await mp_entity.update_attributes()
        except Exception as e:
            _LOG.error(f"Could not trigger deferred update for media player from {self.id}: {e}")