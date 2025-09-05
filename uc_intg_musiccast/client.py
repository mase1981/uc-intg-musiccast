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
            system_version=data.get("system_version", ""),
            api_version=data.get("api_version", ""),
            ip_address=ip_address,
            friendly_name=data.get("model_name", "Yamaha MusicCast")
        )


@dataclass 
class DeviceStatus:
    """Current device status."""
    
    power: str = "standby"
    volume: int = 0
    max_volume: int = 100
    mute: bool = False
    input: str = ""
    sound_program: str = ""
    sleep: int = 0
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "DeviceStatus":
        """Create DeviceStatus from API response."""
        return cls(
            power=data.get("power", "standby"),
            volume=int(data.get("volume", 0)),
            max_volume=int(data.get("max_volume", 100)),
            mute=bool(data.get("mute", False)),
            input=data.get("input", ""),
            sound_program=data.get("sound_program", ""),
            sleep=int(data.get("sleep", 0))
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
        return await self._make_request("system/getFeatures")

    async def get_status(self, zone: str = "main") -> DeviceStatus:
        """Get zone status."""
        data = await self._make_request(f"{zone}/getStatus")
        return DeviceStatus.from_api_response(data)
    
    async def set_power(self, zone: str = "main", power: str = "toggle") -> bool:
        """Set power state."""
        await self._make_request(f"{zone}/setPower", {"power": power})
        return True
    
    async def set_volume(self, zone: str = "main", volume: Optional[int] = None, 
                        step: Optional[int] = None) -> bool:
        """Set volume level or step."""
        params = {}
        if volume is not None:
            params["volume"] = max(0, min(100, volume))
        elif step is not None:
            params["step"] = step
        else:
            raise InvalidParameterError("Either volume or step must be provided")
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

    @classmethod
    async def discover_devices(cls, timeout: int = 10) -> List[Tuple[str, DeviceInfo]]:
        """
        Discover MusicCast devices on network.
        
        Note: This is a placeholder implementation. For full discovery,
        you would implement mDNS/Bonjour discovery or network scanning.
        """
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