"""
Yamaha MusicCast API client implementation.

:copyright: (c) 2025 by Meir Miyara
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp

_LOG = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Yamaha MusicCast device information."""
    
    device_id: str
    model_name: str
    system_version: str
    api_version: str
    ip_address: str
    friendly_name: str = ""
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any], ip_address: str) -> "DeviceInfo":
        """Create DeviceInfo from API response."""
        return cls(
            device_id=data.get("device_id", ""),
            model_name=data.get("model_name", "Unknown"),
            system_version=str(data.get("system_version", "")),
            api_version=str(data.get("api_version", "")),
            ip_address=ip_address,
            friendly_name=data.get("model_name", "Yamaha MusicCast")
        )


@dataclass 
class DeviceStatus:
    """Current device status."""
    
    power: str = "standby"
    volume: int = 0
    max_volume: int = 161
    mute: bool = False
    input: str = ""
    input_text: str = ""
    sound_program: str = ""
    sleep: int = 0
    tone_control: Dict[str, Any] = None
    dialogue_level: int = 0
    subwoofer_volume: int = 0
    actual_volume: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tone_control is None:
            self.tone_control = {"mode": "manual", "bass": 0, "treble": 0}
        if self.actual_volume is None:
            self.actual_volume = {"mode": "db", "value": -80.0, "unit": "dB"}
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "DeviceStatus":
        """Create DeviceStatus from API response."""
        return cls(
            power=data.get("power", "standby"),
            volume=int(data.get("volume", 0)),
            max_volume=int(data.get("max_volume", 161)),
            mute=bool(data.get("mute", False)),
            input=data.get("input", ""),
            input_text=data.get("input_text", ""),
            sound_program=data.get("sound_program", ""),
            sleep=int(data.get("sleep", 0)),
            tone_control=data.get("tone_control", {"mode": "manual", "bass": 0, "treble": 0}),
            dialogue_level=int(data.get("dialogue_level", 0)),
            subwoofer_volume=int(data.get("subwoofer_volume", 0)),
            actual_volume=data.get("actual_volume", {"mode": "db", "value": -80.0, "unit": "dB"})
        )


@dataclass
class PlayInfo:
    """Current playback information."""
    
    playback: str = "stop"
    repeat: str = "off"
    shuffle: str = "off"
    artist: str = ""
    album: str = ""
    track: str = ""
    play_time: int = 0
    total_time: int = 0
    albumart_url: str = ""
    input: str = ""
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "PlayInfo":
        """Create PlayInfo from API response."""
        return cls(
            playback=data.get("playback", "stop"),
            repeat=data.get("repeat", "off"),
            shuffle=data.get("shuffle", "off"),
            artist=data.get("artist", ""),
            album=data.get("album", ""),
            track=data.get("track", ""),
            play_time=int(data.get("play_time", 0)),
            total_time=int(data.get("total_time", 0)),
            albumart_url=data.get("albumart_url", ""),
            input=data.get("input", "")
        )


class YamahaMusicCastError(Exception):
    """Base exception for Yamaha MusicCast API errors."""
    pass


class DeviceNotReachableError(YamahaMusicCastError):
    """Device is not reachable over network."""
    pass


class InvalidParameterError(YamahaMusicCastError):
    """Invalid parameter provided to API."""
    pass


class YamahaMusicCastClient:
    """
    Yamaha MusicCast API client.
    """
    
    def __init__(self, ip_address: str, timeout: int = 10):
        """Initialize client."""
        self.ip_address = ip_address
        self.timeout = timeout
        self.base_url = f"http://{ip_address}"
        self.api_base = f"{self.base_url}/YamahaExtendedControl/v1"
        self._session: Optional[aiohttp.ClientSession] = None
        self._device_capabilities: Optional[Dict[str, Any]] = None
        _LOG.debug(f"Initialized Yamaha client for {ip_address}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to device API."""
        await self._ensure_session()
        
        url = f"{self.api_base}/{endpoint}"
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            if clean_params:
                url += "?" + urlencode(clean_params)
        
        try:
            _LOG.debug(f"Making request to: {url}")
            async with self._session.get(url) as response:
                if response.status != 200:
                    raise DeviceNotReachableError(f"HTTP {response.status}: {response.reason}")
                data = await response.json()
                response_code = data.get("response_code", -1)
                if response_code != 0:
                    error_msg = f"API error code {response_code}"
                    if response_code == 3:
                        raise InvalidParameterError(f"{error_msg}: Invalid zone or parameter")
                    elif response_code == 4:
                        raise InvalidParameterError(f"{error_msg}: Invalid parameter value")
                    else:
                        raise YamahaMusicCastError(error_msg)
                
                _LOG.debug(f"Request successful: {endpoint}")
                return data
                
        except aiohttp.ClientError as e:
            _LOG.error(f"Network error communicating with device {self.ip_address}: {e}")
            raise DeviceNotReachableError(f"Network error: {e}")
        except asyncio.TimeoutError:
            _LOG.error(f"Timeout communicating with device {self.ip_address}")
            raise DeviceNotReachableError("Request timeout")

    async def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        data = await self._make_request("system/getDeviceInfo")
        return DeviceInfo.from_api_response(data, self.ip_address)
    
    async def get_features(self) -> Dict[str, Any]:
        """Get device features and capabilities."""
        if self._device_capabilities is None:
            self._device_capabilities = await self._make_request("system/getFeatures")
        return self._device_capabilities

    async def get_status(self, zone: str = "main") -> DeviceStatus:
        """Get zone status."""
        data = await self._make_request(f"{zone}/getStatus")
        return DeviceStatus.from_api_response(data)
    
    async def set_power(self, zone: str = "main", power: str = "toggle") -> bool:
        """Set power state."""
        await self._make_request(f"{zone}/setPower", {"power": power})
        return True
    
    async def set_volume(self, zone: str = "main", volume: Optional[int] = None, 
                        step: Optional[int] = None, direction: Optional[str] = None) -> bool:
        """Set volume level or step."""
        params = {}
        if volume is not None:
            features = await self.get_features()
            max_vol = 161  # Default for receivers
            
            if "zone" in features:
                for zone_info in features["zone"]:
                    if zone_info.get("id") == zone:
                        range_steps = zone_info.get("range_step", [])
                        for range_step in range_steps:
                            if range_step.get("id") == "volume":
                                max_vol = range_step.get("max", 161)
                                break
                        break
            
            params["volume"] = max(0, min(max_vol, volume))
        elif direction in ["up", "down"]:
            # R-N803D specific format: volume=up/down&step=4
            params["volume"] = direction
            params["step"] = step if step is not None else 4
        elif step is not None:
            params["step"] = step
        else:
            raise InvalidParameterError("Either volume, step, or direction must be provided")
        await self._make_request(f"{zone}/setVolume", params)
        return True
    
    async def set_mute(self, zone: str = "main", enable: bool = False) -> bool:
        """Set mute state."""
        await self._make_request(f"{zone}/setMute", {"enable": "true" if enable else "false"})
        return True
    
    async def set_input(self, zone: str = "main", input_source: str = "") -> bool:
        """Set input source."""
        await self._make_request(f"{zone}/setInput", {"input": input_source})
        return True

    async def set_sound_program(self, zone: str = "main", program: str = "") -> bool:
        """Set sound program."""
        await self._make_request(f"{zone}/setSoundProgram", {"program": program})
        return True
    
    async def set_tone_control(self, zone: str = "main", mode: str = "manual", 
                              bass: Optional[int] = None, treble: Optional[int] = None) -> bool:
        """Set tone control."""
        params = {"mode": mode}
        if bass is not None:
            params["bass"] = max(-12, min(12, bass))
        if treble is not None:
            params["treble"] = max(-12, min(12, treble))
        await self._make_request(f"{zone}/setToneControl", params)
        return True

    async def get_play_info(self) -> PlayInfo:
        """Get current playback information."""
        data = await self._make_request("netusb/getPlayInfo")
        play_info = PlayInfo.from_api_response(data)
        if play_info.albumart_url and play_info.albumart_url.startswith('/'):
            play_info.albumart_url = f"{self.base_url}{play_info.albumart_url}"
        return play_info
    
    async def set_playback(self, playback: str) -> bool:
        """Control playback."""
        command_mapping = {
            "play_pause": "toggle",
            "play": "play",
            "pause": "pause", 
            "stop": "stop",
            "next": "next",
            "previous": "previous"
        }
        
        actual_command = command_mapping.get(playback, playback)
        if actual_command not in command_mapping.values():
            raise InvalidParameterError(f"Invalid playback command: {playback}")
            
        await self._make_request("netusb/setPlayback", {"playback": actual_command})
        return True
    
    async def set_repeat(self, repeat: str) -> bool:
        """Set repeat mode."""
        if repeat not in ["off", "one", "all"]:
            raise InvalidParameterError(f"Invalid repeat mode: {repeat}")
        await self._make_request("netusb/setRepeat", {"repeat": repeat})
        return True

    async def set_shuffle(self, shuffle: str) -> bool:
        """Set shuffle mode."""
        if shuffle not in ["off", "on"]:
            raise InvalidParameterError(f"Invalid shuffle mode: {shuffle}")
        await self._make_request("netusb/setShuffle", {"shuffle": shuffle})
        return True

    async def recall_preset(self, zone: str = "main", num: int = 1) -> bool:
        """Recall a preset (favorites 1-40)."""
        if not (1 <= num <= 40):
            raise InvalidParameterError(f"Preset number must be between 1 and 40, got {num}")
        await self._make_request("netusb/recallPreset", {"zone": zone, "num": num})
        return True

    async def get_preset_info(self) -> Dict[str, Any]:
        """Get preset information."""
        return await self._make_request("netusb/getPresetInfo")

    async def get_list_info(self, list_id: str = "main", input_source: Optional[str] = None, 
                           size: int = 8, lang: str = "en", index: int = 0) -> Dict[str, Any]:
        """Get list information for browsing content."""
        params = {"list_id": list_id, "size": size, "lang": lang, "index": index}
        if input_source:
            params["input"] = input_source
        return await self._make_request("netusb/getListInfo", params)

    async def set_list_control(self, list_id: str = "main", control_type: str = "play", 
                              index: int = 0, zone: str = "main") -> bool:
        """Control list playback and navigation."""
        valid_types = ["play", "select", "return"]
        if control_type not in valid_types:
            raise InvalidParameterError(f"Invalid control type: {control_type}. Must be one of {valid_types}")
        
        params = {"list_id": list_id, "type": control_type, "zone": zone}
        if control_type in ["play", "select"]:
            params["index"] = index
            
        await self._make_request("netusb/setListControl", params)
        return True

    async def manage_play(self, action_type: str, timeout: int = 60000) -> bool:
        """Manage playback actions like thumbs up/down."""
        valid_types = ["thumbs_up", "thumbs_down"]
        if action_type not in valid_types:
            raise InvalidParameterError(f"Invalid action type: {action_type}. Must be one of {valid_types}")
        
        await self._make_request("netusb/managePlay", {"type": action_type, "timeout": timeout})
        return True

    async def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode."""
        await self._make_request("netusb/toggleShuffle")
        return True

    async def toggle_repeat(self) -> bool:
        """Toggle repeat mode."""
        await self._make_request("netusb/toggleRepeat")
        return True

    async def get_available_inputs(self, zone: str = "main") -> List[Dict[str, str]]:
        """Get available inputs for a zone from device capabilities."""
        try:
            features = await self.get_features()
            
            # Get system input list with metadata
            system_inputs = {inp["id"]: inp for inp in features.get("system", {}).get("input_list", [])}
            
            # Get zone-specific input list
            zone_inputs = []
            for zone_info in features.get("zone", []):
                if zone_info.get("id") == zone:
                    zone_inputs = zone_info.get("input_list", [])
                    break
            
            # Build enhanced input list
            enhanced_inputs = []
            input_name_mapping = {
                "hdmi1": "HDMI 1", "hdmi2": "HDMI 2", "hdmi3": "HDMI 3", 
                "hdmi4": "HDMI 4", "hdmi5": "HDMI 5", "hdmi6": "HDMI 6", "hdmi7": "HDMI 7",
                "av1": "AV 1", "av2": "AV 2", "av3": "AV 3",
                "audio1": "Audio 1", "audio2": "Audio 2", "audio3": "Audio 3", "audio4": "Audio 4",
                "bluetooth": "Bluetooth", "spotify": "Spotify", "airplay": "AirPlay",
                "usb": "USB", "tuner": "Tuner", "net_radio": "Net Radio", "phono": "Phono",
                "napster": "Napster", "qobuz": "Qobuz", "tidal": "Tidal", "deezer": "Deezer",
                "amazon_music": "Amazon Music", "alexa": "Alexa", "server": "Server",
                "mc_link": "MusicCast Link", "main_sync": "Main Sync", "tv": "TV",
                "optical1": "Optical 1", "optical2": "Optical 2", "coaxial1": "Coaxial 1", 
                "coaxial2": "Coaxial 2", "line1": "Line 1", "line2": "Line 2", "line3": "Line 3",
                "line_cd": "Line CD", "juke": "Juke"
            }
            
            for input_id in zone_inputs:
                input_info = system_inputs.get(input_id, {})
                friendly_name = input_name_mapping.get(input_id, input_id.replace("_", " ").title())
                
                enhanced_inputs.append({
                    "id": input_id,
                    "name": friendly_name,
                    "distribution_enable": input_info.get("distribution_enable", False),
                    "play_info_type": input_info.get("play_info_type", "none")
                })
            
            _LOG.info(f"Found {len(enhanced_inputs)} inputs for zone {zone}")
            return enhanced_inputs
            
        except Exception as e:
            _LOG.error(f"Failed to get available inputs: {e}")
            # Fallback to basic inputs
            return [
                {"id": "spotify", "name": "Spotify", "distribution_enable": True, "play_info_type": "netusb"},
                {"id": "bluetooth", "name": "Bluetooth", "distribution_enable": True, "play_info_type": "netusb"},
                {"id": "hdmi1", "name": "HDMI 1", "distribution_enable": True, "play_info_type": "none"},
                {"id": "audio1", "name": "Audio 1", "distribution_enable": True, "play_info_type": "none"}
            ]

    async def get_available_sound_programs(self, zone: str = "main") -> List[str]:
        """Get available sound programs for a zone."""
        try:
            features = await self.get_features()
            for zone_info in features.get("zone", []):
                if zone_info.get("id") == zone:
                    programs = zone_info.get("sound_program_list", [])
                    _LOG.info(f"Found {len(programs)} sound programs for zone {zone}")
                    return programs
            return []
        except Exception as e:
            _LOG.error(f"Failed to get sound programs: {e}")
            return []

    @classmethod
    async def discover_devices(cls, timeout: int = 10) -> List[Tuple[str, DeviceInfo]]:

        _LOG.info("Device discovery not implemented, returning empty list")
        return []

    @classmethod  
    async def verify_device(cls, ip_address: str, timeout: int = 5) -> Optional[DeviceInfo]:
        """Verify device at given IP address."""
        try:
            async with cls(ip_address, timeout) as client:
                return await client.get_device_info()
        except Exception as e:
            _LOG.debug(f"Device verification failed for {ip_address}: {e}")
            return None