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
    """Yamaha MusicCast media player entity."""

    def __init__(self, device_id: str, device_name: str):
        """Initialize the media player entity."""
        features = self._build_features()
        attributes = self._build_initial_attributes()

        super().__init__(
            identifier=f"{device_id}_media_player",
            name=device_name,
            features=features,
            attributes=attributes,
            device_class=DeviceClasses.SPEAKER,
            cmd_handler=self._handle_command,
        )

        self._client: Optional[YamahaMusicCastClient] = None
        self._zone: str = "main"
        self._integration_api = None
        self._available_sources = []

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
            Features.REPEAT, Features.SHUFFLE, Features.SELECT_SOURCE  # Added source selection
        ]

    def _build_initial_attributes(self) -> dict:
        """Build initial attributes dictionary."""
        return {
            Attributes.STATE: States.STANDBY,
            Attributes.VOLUME: 0,
            Attributes.MUTED: False,
            Attributes.SOURCE_LIST: [],  # Will be populated after connecting
            Attributes.SOURCE: "",       # Current source
        }

    async def initialize_sources(self):
        """Initialize available sources from device features."""
        if not self._client:
            return

        try:
            features = await self._client.get_features()
            zone_info = features.get("zone", [])
            
            if zone_info:
                # Get input list from main zone
                main_zone = next((z for z in zone_info if z.get("id") == "main"), None)
                if main_zone:
                    input_list = main_zone.get("input_list", [])
                    
                    # Map technical input names to friendly names
                    source_mapping = {
                        "hdmi": "HDMI",
                        "analog": "Analog",
                        "bluetooth": "Bluetooth", 
                        "spotify": "Spotify",
                        "airplay": "AirPlay",
                        "usb": "USB",
                        "optical": "Optical",
                        "coaxial": "Coaxial",
                        "aux": "AUX"
                    }
                    
                    self._available_sources = []
                    for input_id in input_list:
                        friendly_name = source_mapping.get(input_id, input_id.title())
                        self._available_sources.append({
                            "id": input_id,
                            "name": friendly_name
                        })
                    
                    # Update source list attribute
                    source_names = [src["name"] for src in self._available_sources]
                    self.attributes[Attributes.SOURCE_LIST] = source_names
                    
                    _LOG.info(f"Initialized {len(self._available_sources)} sources: {source_names}")
            
        except Exception as e:
            _LOG.error(f"Failed to initialize sources: {e}")
            # Fallback to common sources
            self._available_sources = [
                {"id": "spotify", "name": "Spotify"},
                {"id": "bluetooth", "name": "Bluetooth"},
                {"id": "hdmi", "name": "HDMI"},
                {"id": "analog", "name": "Analog"}
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
            self.attributes[Attributes.VOLUME] = status.volume
            self.attributes[Attributes.MUTED] = status.mute

            # Update current source
            current_input = status.input
            current_source = next(
                (src["name"] for src in self._available_sources if src["id"] == current_input),
                current_input.title()
            )
            self.attributes[Attributes.SOURCE] = current_source

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
            _LOG.error(f"Failed to update state: {e}")
            self.attributes[Attributes.STATE] = States.UNAVAILABLE
            self._force_integration_update()

    def _force_integration_update(self):
        """Force update to integration API."""
        if self._integration_api and hasattr(self._integration_api, 'configured_entities'):
            try:
                self._integration_api.configured_entities.update_attributes(
                    self.id, self.attributes
                )
            except Exception as e:
                _LOG.debug("Could not update integration API: %s", e)

    async def _handle_command(self, entity, cmd_id: str, params: dict = None) -> ucapi.StatusCodes:
        """Handle media player commands."""
        if not self._client:
            return ucapi.StatusCodes.SERVER_ERROR

        try:
            _LOG.info(f"Handling media player command: {cmd_id} with params: {params}")
            
            if cmd_id == Commands.ON:
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
                await self._client.set_volume(self._zone, volume=params['volume'])
            elif cmd_id == Commands.VOLUME_UP:
                await self._client.set_volume(self._zone, step=1)
            elif cmd_id == Commands.VOLUME_DOWN:
                await self._client.set_volume(self._zone, step=-1)
            elif cmd_id == Commands.MUTE_TOGGLE:
                current_mute = self.attributes.get(Attributes.MUTED, False)
                await self._client.set_mute(self._zone, enable=not current_mute)
            elif cmd_id == Commands.REPEAT and params and 'repeat' in params:
                # Map ucapi repeat modes to MusicCast
                repeat_map = {"OFF": "off", "ONE": "one", "ALL": "all"}
                repeat_mode = repeat_map.get(params['repeat'], "off")
                await self._client.set_repeat(repeat_mode)
            elif cmd_id == Commands.SHUFFLE and params and 'shuffle' in params:
                shuffle_mode = "on" if params['shuffle'] else "off"
                await self._client.set_shuffle(shuffle_mode)
            elif cmd_id == Commands.SELECT_SOURCE and params and 'source' in params:
                # Handle source selection
                source_name = params['source']
                source_id = next(
                    (src["id"] for src in self._available_sources if src["name"] == source_name),
                    None
                )
                if source_id:
                    await self._client.set_input(self._zone, source_id)
                    _LOG.info(f"Switched to source: {source_name} ({source_id})")
                else:
                    _LOG.error(f"Unknown source: {source_name}")
                    return ucapi.StatusCodes.BAD_REQUEST
            else:
                _LOG.warning(f"Unhandled command: {cmd_id}")
                return ucapi.StatusCodes.NOT_IMPLEMENTED

            # Defer update to allow device to respond
            asyncio.create_task(self._deferred_update())
            return ucapi.StatusCodes.OK

        except Exception as e:
            _LOG.error(f"Error handling command {cmd_id}: {e}")
            return ucapi.StatusCodes.SERVER_ERROR

    async def _deferred_update(self):
        """Update attributes after a short delay."""
        await asyncio.sleep(0.5)
        await self.update_attributes()