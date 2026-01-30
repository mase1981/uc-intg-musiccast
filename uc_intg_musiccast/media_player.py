"""
Yamaha MusicCast Media Player Entity.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import ucapi
from ucapi.media_player import (
    Attributes, Commands, DeviceClasses, Features, MediaPlayer, States
)

from uc_intg_musiccast.client import YamahaMusicCastClient

_LOG = logging.getLogger(__name__)

class YamahaMusicCastMediaPlayer(MediaPlayer):

    def __init__(self, entity_id: str, device_name: str):
        features = self._build_features()
        attributes = self._build_initial_attributes()
        options = self._build_options()

        super().__init__(
            identifier=entity_id,  # Use provided entity_id for multi-device support
            name=device_name,     # Each device gets its own name
            features=features,
            attributes=attributes,
            device_class=DeviceClasses.RECEIVER,  # Changed to RECEIVER for AVR devices
            options=options,
            cmd_handler=self._handle_command,
        )

        self._client: Optional[YamahaMusicCastClient] = None
        self._zone: str = "main"
        self._integration_api = None
        self._available_sources = []
        self._available_sound_programs = []
        self._device_capabilities = {}

    def set_client(self, client):
        """Set the MusicCast API client."""
        self._client = client

    def _build_features(self) -> list:
        """Build supported features list."""
        return [
            Features.ON_OFF, Features.PLAY_PAUSE, Features.STOP,
            Features.NEXT, Features.PREVIOUS, Features.VOLUME,
            Features.VOLUME_UP_DOWN, Features.MUTE_TOGGLE, Features.MEDIA_TITLE,
            Features.MEDIA_ARTIST, Features.MEDIA_ALBUM, Features.MEDIA_IMAGE_URL,
            Features.MEDIA_DURATION, Features.MEDIA_POSITION,
            Features.REPEAT, Features.SHUFFLE, Features.SELECT_SOURCE,
            Features.SELECT_SOUND_MODE  # Added sound mode selection
        ]

    def _build_initial_attributes(self) -> dict:
        """Build initial attributes dictionary."""
        return {
            Attributes.STATE: States.STANDBY,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE_LIST: [],
            Attributes.SOURCE: "",
            Attributes.SOUND_MODE_LIST: [],
            Attributes.SOUND_MODE: "",
        }

    def _build_options(self) -> dict:
        """Build entity options including simple commands for activity support."""
        return {
            "simple_commands": [
                "PLAY",
                "PAUSE",
                "PLAY_PAUSE",
                "STOP",
                "NEXT",
                "PREVIOUS",
                "VOLUME_UP",
                "VOLUME_DOWN",
                "MUTE_TOGGLE"
            ]
        }

    async def initialize_sources(self):
        """Initialize available sources and capabilities from device."""
        if not self._client:
            return

        try:
            # Get device capabilities
            features = await self._client.get_features()
            self._device_capabilities = features
            
            # Get available inputs
            available_inputs = await self._client.get_available_inputs(self._zone)
            self._available_sources = available_inputs
            
            # Update source list attribute
            source_names = [src["name"] for src in self._available_sources]
            self.attributes[Attributes.SOURCE_LIST] = source_names
            
            # Get available sound programs
            sound_programs = await self._client.get_available_sound_programs(self._zone)
            self._available_sound_programs = sound_programs
            
            # Create friendly sound mode names
            sound_mode_mapping = {
                "munich": "Munich Hall",
                "vienna": "Vienna Hall",
                "amsterdam": "Amsterdam Concert Hall",
                "freiburg": "Freiburg Cathedral",
                "royaumont": "Royaumont Abbey",
                "chamber": "Chamber Music",
                "village_vanguard": "Village Vanguard Jazz Club",
                "warehouse_loft": "Warehouse Loft",
                "cellar_club": "Cellar Club",
                "roxy_theatre": "Roxy Theatre",
                "bottom_line": "Bottom Line",
                "sports": "Sports",
                "action_game": "Action Game",
                "roleplaying_game": "RPG Game",
                "music_video": "Music Video",
                "recital_opera": "Recital/Opera",
                "standard": "Standard",
                "spectacle": "Spectacle",
                "sci-fi": "Sci-Fi",
                "adventure": "Adventure",
                "drama": "Drama",
                "mono_movie": "Mono Movie",
                "enhanced": "Enhanced",
                "2ch_stereo": "2-Channel Stereo",
                "all_ch_stereo": "All Channel Stereo",
                "surr_decoder": "Surround Decoder",
                "straight": "Straight"
            }
            
            # Update sound mode list
            sound_mode_names = []
            for program in sound_programs:
                friendly_name = sound_mode_mapping.get(program, program.replace("_", " ").title())
                sound_mode_names.append(friendly_name)
            
            self.attributes[Attributes.SOUND_MODE_LIST] = sound_mode_names
            
            _LOG.info(f"Initialized {len(self._available_sources)} sources and {len(sound_programs)} sound programs for {self.id}")
            
        except Exception as e:
            _LOG.error(f"Failed to initialize capabilities for {self.id}: {e}")
            # Fallback to basic setup
            self._available_sources = [
                {"id": "spotify", "name": "Spotify", "distribution_enable": True, "play_info_type": "netusb"},
                {"id": "bluetooth", "name": "Bluetooth", "distribution_enable": True, "play_info_type": "netusb"},
                {"id": "hdmi1", "name": "HDMI 1", "distribution_enable": True, "play_info_type": "none"}
            ]
            self.attributes[Attributes.SOURCE_LIST] = [src["name"] for src in self._available_sources]

    async def update_attributes(self):
        """Update entity attributes from device state."""
        if not self._client:
            return

        try:
            status = await self._client.get_status(self._zone)
            play_info = await self._client.get_play_info()

            # Update power and volume state
            new_state = States.ON if status.power == "on" else States.STANDBY
            if new_state == States.ON:
                if play_info.playback == "play":
                    new_state = States.PLAYING
                elif play_info.playback == "pause":
                    new_state = States.PAUSED
                elif play_info.playback == "stop":
                    new_state = States.ON

            self.attributes[Attributes.STATE] = new_state
            
            self.attributes[Attributes.VOLUME] = self._convert_volume_to_percentage(
                status.volume, status.max_volume
            )
            self.attributes[Attributes.MUTED] = status.mute

            # Update current source
            current_input = status.input
            current_source = next(
                (src["name"] for src in self._available_sources if src["id"] == current_input),
                status.input_text or current_input.replace("_", " ").title()
            )
            self.attributes[Attributes.SOURCE] = current_source

            # Update current sound mode
            current_program = status.sound_program
            if current_program and self._available_sound_programs:
                # Find friendly name for current sound program
                sound_mode_mapping = {
                    "munich": "Munich Hall", "vienna": "Vienna Hall", "amsterdam": "Amsterdam Concert Hall",
                    "2ch_stereo": "2-Channel Stereo", "all_ch_stereo": "All Channel Stereo",
                    "straight": "Straight", "standard": "Standard"
                }
                current_sound_mode = sound_mode_mapping.get(
                    current_program, current_program.replace("_", " ").title()
                )
                self.attributes[Attributes.SOUND_MODE] = current_sound_mode

            # Update media info
            if new_state in [States.PLAYING, States.PAUSED]:
                self.attributes[Attributes.MEDIA_TITLE] = play_info.track
                self.attributes[Attributes.MEDIA_ARTIST] = play_info.artist
                self.attributes[Attributes.MEDIA_ALBUM] = play_info.album
                self.attributes[Attributes.MEDIA_IMAGE_URL] = play_info.albumart_url
                self.attributes[Attributes.MEDIA_DURATION] = play_info.total_time
                self.attributes[Attributes.MEDIA_POSITION] = play_info.play_time
                self.attributes[Attributes.MEDIA_POSITION_UPDATED_AT] = datetime.utcnow().isoformat()
                self.attributes[Attributes.REPEAT] = play_info.repeat
                self.attributes[Attributes.SHUFFLE] = play_info.shuffle == "on"
            else:
                # Clear media info when not playing
                for attr in [Attributes.MEDIA_TITLE, Attributes.MEDIA_ARTIST, Attributes.MEDIA_ALBUM, 
                           Attributes.MEDIA_IMAGE_URL, Attributes.MEDIA_DURATION, Attributes.MEDIA_POSITION]:
                    self.attributes.pop(attr, None)
            
            self._force_integration_update()

        except Exception as e:
            _LOG.error(f"Failed to update state for {self.id}: {e}")
            self.attributes[Attributes.STATE] = States.UNAVAILABLE
            self._force_integration_update()

    def _convert_volume_to_percentage(self, volume: int, max_volume: int) -> int:
        """Convert device volume to percentage (0-100)."""
        if max_volume <= 0:
            return 0
        return min(100, max(0, int((volume / max_volume) * 100)))

    def _convert_percentage_to_volume(self, percentage: int, max_volume: int) -> int:
        """Convert percentage (0-100) to device volume."""
        return min(max_volume, max(0, int((percentage / 100) * max_volume)))

    def _force_integration_update(self):
        """Force update to integration API."""
        if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
            try:
                self._integration_api.configured_entities.update_attributes(
                    self.id, self.attributes
                )
            except Exception as e:
                _LOG.debug("Could not update integration API for %s: %s", self.id, e)

    async def _handle_command(self, entity, cmd_id: str, params: dict = None) -> ucapi.StatusCodes:
        """Handle media player commands."""
        if not self._client:
            return ucapi.StatusCodes.SERVER_ERROR

        try:
            _LOG.info(f"Handling media player command for {self.id}: {cmd_id} with params: {params}")

            # Handle simple commands from activities
            if cmd_id == "PLAY":
                await self._client.set_playback("play")
            elif cmd_id == "PAUSE":
                await self._client.set_playback("pause")
            elif cmd_id == "PLAY_PAUSE":
                await self._client.set_playback("play_pause")
            elif cmd_id == "STOP":
                await self._client.set_playback("stop")
            elif cmd_id == "NEXT":
                await self._client.set_playback("next")
            elif cmd_id == "PREVIOUS":
                await self._client.set_playback("previous")
            elif cmd_id == "VOLUME_UP":
                await self._client.set_volume(self._zone, direction="up", step=1)
            elif cmd_id == "VOLUME_DOWN":
                await self._client.set_volume(self._zone, direction="down", step=1)
            elif cmd_id == "MUTE_TOGGLE":
                current_mute = self.attributes.get(Attributes.MUTED, False)
                await self._client.set_mute(self._zone, enable=not current_mute)
            # Handle standard entity commands
            elif cmd_id == Commands.ON:
                await self._client.set_power(self._zone, "on")
            elif cmd_id == Commands.OFF:
                await self._client.set_power(self._zone, "standby")
            elif cmd_id == Commands.PLAY_PAUSE:
                await self._client.set_playback("play_pause")
            elif cmd_id == Commands.STOP:
                await self._client.set_playback("stop")
            elif cmd_id == Commands.NEXT:
                await self._client.set_playback("next")
            elif cmd_id == Commands.PREVIOUS:
                await self._client.set_playback("previous")
            elif cmd_id == Commands.VOLUME and params and 'volume' in params:
                percentage = params['volume']
                status = await self._client.get_status(self._zone)
                device_volume = self._convert_percentage_to_volume(percentage, status.max_volume)
                await self._client.set_volume(self._zone, volume=device_volume)
            elif cmd_id == Commands.VOLUME_UP:
                await self._client.set_volume(self._zone, direction="up", step=1)
            elif cmd_id == Commands.VOLUME_DOWN:
                await self._client.set_volume(self._zone, direction="down", step=1)
            elif cmd_id == Commands.MUTE_TOGGLE:
                current_mute = self.attributes.get(Attributes.MUTED, False)
                await self._client.set_mute(self._zone, enable=not current_mute)
            elif cmd_id == Commands.REPEAT and params and 'repeat' in params:
                repeat_map = {"OFF": "off", "ONE": "one", "ALL": "all"}
                repeat_mode = repeat_map.get(params['repeat'], "off")
                await self._client.set_repeat(repeat_mode)
            elif cmd_id == Commands.SHUFFLE and params and 'shuffle' in params:
                shuffle_mode = "on" if params['shuffle'] else "off"
                await self._client.set_shuffle(shuffle_mode)
            elif cmd_id == Commands.SELECT_SOURCE and params and 'source' in params:
                source_name = params['source']
                source_id = next(
                    (src["id"] for src in self._available_sources if src["name"] == source_name),
                    None
                )
                if source_id:
                    await self._client.set_input(self._zone, source_id)
                    _LOG.info(f"Switched to source: {source_name} ({source_id}) for {self.id}")
                else:
                    _LOG.error(f"Unknown source: {source_name} for {self.id}")
                    return ucapi.StatusCodes.BAD_REQUEST
            elif cmd_id == Commands.SELECT_SOUND_MODE and params and 'sound_mode' in params:
                sound_mode_name = params['sound_mode']
                
                sound_mode_reverse_mapping = {
                    "Munich Hall": "munich", "Vienna Hall": "vienna", "Amsterdam Concert Hall": "amsterdam",
                    "2-Channel Stereo": "2ch_stereo", "All Channel Stereo": "all_ch_stereo",
                    "Straight": "straight", "Standard": "standard", "Sports": "sports",
                    "Action Game": "action_game", "RPG Game": "roleplaying_game"
                }
                
                program_id = sound_mode_reverse_mapping.get(sound_mode_name)
                if not program_id:
                    program_id = next(
                        (prog for prog in self._available_sound_programs 
                         if prog.replace("_", " ").title() == sound_mode_name),
                        None
                    )
                if not program_id:
                    program_id = sound_mode_name.lower().replace(" ", "_")
                
                if program_id and program_id in self._available_sound_programs:
                    await self._client.set_sound_program(self._zone, program_id)
                    _LOG.info(f"Switched to sound mode: {sound_mode_name} ({program_id}) for {self.id}")
                else:
                    _LOG.error(f"Unknown sound mode: {sound_mode_name} for {self.id}")
                    return ucapi.StatusCodes.BAD_REQUEST
            else:
                _LOG.warning(f"Unhandled command: {cmd_id} for {self.id}")
                return ucapi.StatusCodes.NOT_IMPLEMENTED

            asyncio.create_task(self._deferred_update())
            return ucapi.StatusCodes.OK

        except Exception as e:
            _LOG.error(f"Error handling command {cmd_id} for {self.id}: {e}")
            return ucapi.StatusCodes.SERVER_ERROR

    async def _deferred_update(self):
        """Update attributes after a short delay."""
        await asyncio.sleep(0.5)
        await self.update_attributes()