#!/usr/bin/env python3
"""
Yamaha MusicCast Device Simulator with Multi-Device Support.


:copyright: (c) 2025 by Meir Miyara
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import json
import logging
import random
import socket
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from aiohttp import web, WSMsgType
from aiohttp.web import Request, Response, WebSocketResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the local IP address of the machine."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


class MusicCastSimulator:
    """Simulates a Yamaha MusicCast audio device."""
    
    def __init__(self, host: str = None, port: int = 8080, device_name: str = "YAS-209-SIM", device_id: int = 1):
        """Initialize the simulator."""
        self.host = host if host else get_local_ip()
        self.port = port
        self.device_name = device_name
        self.device_id = device_id
        self.app = web.Application()
        self.websocket_clients: Set[WebSocketResponse] = set()
        
        # Device state - MusicCast specific with unique data per device
        self.device_state = {
            "power": "on",
            "volume": 20 + (device_id * 5),  # Different volumes per device
            "max_volume": 100,
            "mute": False,
            "input": "spotify" if device_id == 1 else "bluetooth" if device_id == 2 else "hdmi1",
            "sound_program": "stereo"
        }

        # Simulated media state
        self.media_state = {
            "playback": "play" if device_id == 1 else "pause" if device_id == 2 else "stop",
            "repeat": "off",
            "shuffle": "off",
            "artist": f"MusicCast Artist {device_id}",
            "album": f"Test Album {device_id}", 
            "track": f"Demo Song {device_id}",
            "play_time": 45 + (device_id * 10),
            "total_time": 180,
            "albumart_url": f"https://via.placeholder.com/300x300/1a1a1a/ffffff?text=MusicCast+{device_id}"
        }
        
        # Device info
        self.device_info = {
            "model_name": f"YAS-209-SIM-{device_id}",
            "device_id": f"SIM{device_id:06d}",
            "system_id": f"1234567{device_id}",
            "system_version": "1.70",
            "api_version": "1.17"
        }
        
        self._setup_routes()
        self._position_task: Optional[asyncio.Task] = None
        self._start_position_update()
        
    def _setup_routes(self):
        """Set up HTTP routes for MusicCast API."""
        # Root endpoint
        self.app.router.add_get('/', self.handle_root)
        
        # System API endpoints
        self.app.router.add_get('/YamahaExtendedControl/v1/system/getDeviceInfo', self.get_device_info)
        self.app.router.add_get('/YamahaExtendedControl/v1/system/getFeatures', self.get_features)
        self.app.router.add_get('/YamahaExtendedControl/v1/system/getNetworkStatus', self.get_network_status)
        
        # Zone control endpoints
        self.app.router.add_get('/YamahaExtendedControl/v1/{zone}/getStatus', self.get_status)
        self.app.router.add_get('/YamahaExtendedControl/v1/{zone}/setPower', self.set_power)
        self.app.router.add_get('/YamahaExtendedControl/v1/{zone}/setVolume', self.set_volume)
        self.app.router.add_get('/YamahaExtendedControl/v1/{zone}/setMute', self.set_mute)
        self.app.router.add_get('/YamahaExtendedControl/v1/{zone}/setInput', self.set_input)
        self.app.router.add_get('/YamahaExtendedControl/v1/{zone}/setSoundProgram', self.set_sound_program)
        
        # NetUSB/Media endpoints
        self.app.router.add_get('/YamahaExtendedControl/v1/netusb/getPlayInfo', self.get_play_info)
        self.app.router.add_get('/YamahaExtendedControl/v1/netusb/setPlayback', self.set_playback)
        self.app.router.add_get('/YamahaExtendedControl/v1/netusb/setRepeat', self.set_repeat)
        self.app.router.add_get('/YamahaExtendedControl/v1/netusb/setShuffle', self.set_shuffle)
        self.app.router.add_put('/YamahaExtendedControl/v1/netusb/setRepeat', self.set_repeat)
        self.app.router.add_put('/YamahaExtendedControl/v1/netusb/setShuffle', self.set_shuffle)
        
        # Additional endpoints
        self.app.router.add_get('/YamahaExtendedControl/v1/netusb/getPresetInfo', self.get_preset_info)
        self.app.router.add_get('/YamahaExtendedControl/v1/netusb/recallPreset', self.recall_preset)
        
        # Health check
        self.app.router.add_get('/health', self.health_check)
        
        # Debug endpoints
        self.app.router.add_get('/debug/state', self.debug_state)
        self.app.router.add_get('/debug/reset', self.debug_reset)
    
    async def handle_root(self, request: Request) -> Response:
        """Handle root endpoint."""
        return web.json_response({
            "message": f"Yamaha MusicCast Simulator {self.device_id}",
            "device_id": self.device_info["device_id"],
            "model": self.device_info["model_name"],
            "device_name": self.device_name,
            "endpoints": [
                "/YamahaExtendedControl/v1/system/getDeviceInfo",
                "/YamahaExtendedControl/v1/system/getFeatures",
                "/YamahaExtendedControl/v1/main/getStatus",
                "/YamahaExtendedControl/v1/main/setPower?power=on|standby|toggle",
                "/YamahaExtendedControl/v1/main/setVolume?volume=0-100",
                "/YamahaExtendedControl/v1/main/setMute?enable=true|false",
                "/YamahaExtendedControl/v1/main/setInput?input=hdmi1|analog|bluetooth|spotify",
                "/YamahaExtendedControl/v1/netusb/getPlayInfo",
                "/YamahaExtendedControl/v1/netusb/setPlayback?playback=play|pause|stop|toggle|next|previous",
                "/YamahaExtendedControl/v1/netusb/setRepeat?repeat=off|one|all",
                "/YamahaExtendedControl/v1/netusb/setShuffle?shuffle=off|on"
            ]
        })

    async def health_check(self, request: Request) -> Response:
        """Health check endpoint for Docker."""
        return web.json_response({
            "status": "healthy", 
            "device_id": self.device_info["device_id"],
            "device_name": self.device_name
        })

    # System API endpoints
    async def get_device_info(self, request: Request) -> Response:
        """Get device information."""
        return web.json_response({
            "response_code": 0,
            **self.device_info
        })

    async def get_features(self, request: Request) -> Response:
        """Get device features and capabilities."""
        return web.json_response({
            "response_code": 0,
            "system": {
                "func_list": ["wired_lan", "wireless_lan", "extend"],
                "zone_num": 1,
                "input_list": [
                    {"id": "hdmi1", "distribution_enable": True, "rename_enable": True, "account_enable": False},
                    {"id": "hdmi2", "distribution_enable": True, "rename_enable": True, "account_enable": False},
                    {"id": "analog", "distribution_enable": True, "rename_enable": True, "account_enable": False},
                    {"id": "bluetooth", "distribution_enable": True, "rename_enable": False, "account_enable": False},
                    {"id": "spotify", "distribution_enable": True, "rename_enable": False, "account_enable": True},
                    {"id": "airplay", "distribution_enable": True, "rename_enable": False, "account_enable": False}
                ]
            },
            "zone": [
                {
                    "id": "main",
                    "func_list": ["power", "volume", "mute", "sound_program"],
                    "input_list": ["hdmi1", "hdmi2", "analog", "bluetooth", "spotify", "airplay"],
                    "sound_program_list": ["stereo", "standard", "surround", "movie", "music", "sports"],
                    "range_step": [
                        {"id": "volume", "min": 0, "max": 100, "step": 1}
                    ]
                }
            ],
            "netusb": {
                "func_list": ["play_info", "play_control"],
                "preset": {"num": 40}
            }
        })

    async def get_network_status(self, request: Request) -> Response:
        """Get network status."""
        return web.json_response({
            "response_code": 0,
            "network_name": f"MusicCast_{self.device_id}",
            "connection": "wireless",
            "dhcp": True,
            "ip_address": self.host,
            "subnet_mask": "255.255.255.0",
            "default_gateway": "192.168.1.1",
            "dns_server_1": "8.8.8.8",
            "dns_server_2": "8.8.4.4",
            "wireless_direct": {"enable": False},
            "wireless_lan": {"enable": True, "frequency": "2.4GHz", "ssid": f"TestNetwork_{self.device_id}"}
        })

    # Zone control endpoints
    async def get_status(self, request: Request) -> Response:
        """Get zone status."""
        zone = request.match_info["zone"]
        if zone != "main":
            return web.json_response({"response_code": 3})
        
        return web.json_response({
            "response_code": 0,
            **self.device_state
        })

    async def set_power(self, request: Request) -> Response:
        """Set power state."""
        zone = request.match_info["zone"]
        if zone != "main":
            return web.json_response({"response_code": 3})
        
        power = request.query.get('power', 'toggle')
        
        if power == "toggle":
            self.device_state["power"] = "on" if self.device_state["power"] == "standby" else "standby"
        elif power in ["on", "standby"]:
            self.device_state["power"] = power
        else:
            return web.json_response({"response_code": 4})
        
        # When turning off, stop playback
        if self.device_state["power"] == "standby":
            self.media_state["playback"] = "stop"
    
        logger.info(f"Device {self.device_id}: Power set to: {self.device_state['power']}")
        await self._broadcast_event({
            "type": "power_change",
            "power": self.device_state["power"]
        })
        return web.json_response({"response_code": 0})

    async def set_volume(self, request: Request) -> Response:
        """Set volume level."""
        zone = request.match_info["zone"]
        if zone != "main":
            return web.json_response({"response_code": 3})
        
        volume = request.query.get('volume')
        step = request.query.get('step')
        
        if volume is not None:
            try:
                vol = max(0, min(self.device_state["max_volume"], int(volume)))
                self.device_state["volume"] = vol
            except ValueError:
                return web.json_response({"response_code": 4})
        elif step is not None:
            try:
                step_val = int(step)
                new_vol = self.device_state["volume"] + step_val
                self.device_state["volume"] = max(0, min(self.device_state["max_volume"], new_vol))
            except ValueError:
                return web.json_response({"response_code": 4})
        else:
            return web.json_response({"response_code": 4})
    
        logger.info(f"Device {self.device_id}: Volume set to: {self.device_state['volume']}")
        await self._broadcast_event({
            "type": "volume_change",
            "volume": self.device_state["volume"]
        })
        return web.json_response({"response_code": 0})

    async def set_mute(self, request: Request) -> Response:
        """Set mute state."""
        zone = request.match_info["zone"]
        if zone != "main":
            return web.json_response({"response_code": 3})
        
        enable = request.query.get('enable', '').lower() == 'true'
        
        self.device_state["mute"] = enable
    
        logger.info(f"Device {self.device_id}: Mute set to: {self.device_state['mute']}")
        await self._broadcast_event({
            "type": "mute_change",
            "mute": self.device_state["mute"]
        })
        return web.json_response({"response_code": 0})

    async def set_input(self, request: Request) -> Response:
        """Set input source."""
        zone = request.match_info["zone"]
        if zone != "main":
            return web.json_response({"response_code": 3})
        
        input_source = request.query.get('input')
        valid_inputs = ["hdmi1", "hdmi2", "analog", "bluetooth", "spotify", "airplay"]
        
        if input_source not in valid_inputs:
            return web.json_response({"response_code": 4})
        
        old_input = self.device_state["input"]
        self.device_state["input"] = input_source
        
        # Change media content based on input
        if input_source == "spotify":
            self.media_state.update({
                "artist": f"Spotify Artist {self.device_id}",
                "album": f"Streaming Album {self.device_id}",
                "track": f"Popular Song {self.device_id}",
                "albumart_url": f"https://via.placeholder.com/300x300/1DB954/ffffff?text=Spotify+{self.device_id}"
            })
        elif input_source == "bluetooth":
            self.media_state.update({
                "artist": f"Bluetooth Device {self.device_id}",
                "album": f"Phone Music {self.device_id}",
                "track": f"BT Audio {self.device_id}",
                "albumart_url": f"https://via.placeholder.com/300x300/0082FC/ffffff?text=BT+{self.device_id}"
            })
        elif input_source.startswith("hdmi"):
            self.media_state.update({
                "artist": f"HDMI Source {self.device_id}",
                "album": f"External Device {self.device_id}",
                "track": f"HDMI Audio {self.device_id}",
                "albumart_url": f"https://via.placeholder.com/300x300/FF6B35/ffffff?text=HDMI+{self.device_id}"
            })
        elif input_source == "analog":
            self.media_state.update({
                "artist": f"Analog Input {self.device_id}",
                "album": f"Line In {self.device_id}",
                "track": f"Analog Audio {self.device_id}",
                "albumart_url": f"https://via.placeholder.com/300x300/4ECDC4/ffffff?text=Analog+{self.device_id}"
            })
        elif input_source == "airplay":
            self.media_state.update({
                "artist": f"AirPlay Device {self.device_id}",
                "album": f"iOS Music {self.device_id}",
                "track": f"AirPlay Audio {self.device_id}",
                "albumart_url": f"https://via.placeholder.com/300x300/007AFF/ffffff?text=AirPlay+{self.device_id}"
            })
    
        logger.info(f"Device {self.device_id}: Input changed from {old_input} to {input_source}")
        await self._broadcast_event({
            "type": "input_change",
            "input": input_source
        })
        return web.json_response({"response_code": 0})

    async def set_sound_program(self, request: Request) -> Response:
        """Set sound program."""
        zone = request.match_info["zone"]
        if zone != "main":
            return web.json_response({"response_code": 3})
        
        program = request.query.get('program')
        valid_programs = ["stereo", "standard", "surround", "movie", "music", "sports"]
        
        if program not in valid_programs:
            return web.json_response({"response_code": 4})
        
        self.device_state["sound_program"] = program
    
        logger.info(f"Device {self.device_id}: Sound program set to: {program}")
        await self._broadcast_event({
            "type": "sound_program_change",
            "program": program
        })
        return web.json_response({"response_code": 0})

    # NetUSB/Media endpoints
    async def get_play_info(self, request: Request) -> Response:
        """Get current playback information."""
        return web.json_response({
            "response_code": 0,
            "input": self.device_state["input"],
            **self.media_state,
            "repeat_available": ["off", "one", "all"],
            "shuffle_available": ["off", "on"]
        })

    async def set_playback(self, request: Request) -> Response:
        """Control playback."""
        playback = request.query.get('playback')
        valid_commands = ["play", "pause", "stop", "previous", "next", "toggle"]
        
        if playback not in valid_commands:
            logger.error(f"Device {self.device_id}: Invalid playback command received: {playback}")
            return web.json_response({"response_code": 4})
        
        if playback == "toggle":
            if self.media_state["playback"] == "play":
                self.media_state["playback"] = "pause"
            elif self.media_state["playback"] in ["pause", "stop"]:
                self.media_state["playback"] = "play"
        elif playback in ["play", "pause", "stop"]:
            self.media_state["playback"] = playback
        elif playback == "next":
            # Simulate track change
            await self._change_track()
            if self.media_state["playback"] != "stop":
                self.media_state["playback"] = "play"
        elif playback == "previous":
            # Simulate track change
            await self._change_track()
            if self.media_state["playback"] != "stop":
                self.media_state["playback"] = "play"
    
        logger.info(f"Device {self.device_id}: Playback command: {playback} -> current state: {self.media_state['playback']}")
        await self._broadcast_event({
            "type": "playback_change",
            "command": playback,
            "state": self.media_state["playback"]
        })
        return web.json_response({"response_code": 0})

    async def set_repeat(self, request: Request) -> Response:
        """Set repeat mode."""
        repeat = request.query.get('repeat')
        valid_modes = ["off", "one", "all"]
        
        if repeat not in valid_modes:
            logger.error(f"Device {self.device_id}: Invalid repeat mode received: {repeat}")
            return web.json_response({"response_code": 4})
        
        self.media_state["repeat"] = repeat
    
        logger.info(f"Device {self.device_id}: Repeat set to: {repeat}")
        await self._broadcast_event({
            "type": "repeat_change",
            "repeat": repeat
        })
        return web.json_response({"response_code": 0})

    async def set_shuffle(self, request: Request) -> Response:
        """Set shuffle mode."""
        shuffle = request.query.get('shuffle')
        valid_modes = ["off", "on"]
        
        if shuffle not in valid_modes:
            logger.error(f"Device {self.device_id}: Invalid shuffle mode received: {shuffle}")
            return web.json_response({"response_code": 4})
        
        self.media_state["shuffle"] = shuffle
    
        logger.info(f"Device {self.device_id}: Shuffle set to: {shuffle}")
        await self._broadcast_event({
            "type": "shuffle_change",
            "shuffle": shuffle
        })
        return web.json_response({"response_code": 0})

    # Additional endpoints
    async def get_preset_info(self, request: Request) -> Response:
        """Get preset information."""
        return web.json_response({
            "response_code": 0,
            "preset_info": [
                {"input": "spotify", "text": f"My Playlist {self.device_id}-1", "attribute": 0},
                {"input": "spotify", "text": f"My Playlist {self.device_id}-2", "attribute": 0},
                {"input": "spotify", "text": f"Favorites {self.device_id}", "attribute": 0}
            ]
        })

    async def recall_preset(self, request: Request) -> Response:
        """Recall a preset."""
        zone = request.query.get('zone', 'main')
        num = request.query.get('num', '1')
        
        try:
            preset_num = int(num)
            if 1 <= preset_num <= 40:
                # Simulate preset recall
                self.media_state.update({
                    "track": f"Preset {preset_num} Song - Device {self.device_id}",
                    "artist": f"Preset {preset_num} Artist - Device {self.device_id}",
                    "album": f"Preset {preset_num} Album - Device {self.device_id}",
                    "playback": "play",
                    "play_time": 0
                })
                
                logger.info(f"Device {self.device_id}: Recalled preset {preset_num}")
                await self._broadcast_event({
                    "type": "preset_recall",
                    "preset": preset_num
                })
                return web.json_response({"response_code": 0})
            else:
                return web.json_response({"response_code": 4})
        except ValueError:
            return web.json_response({"response_code": 4})

    # Debug endpoints
    async def debug_state(self, request: Request) -> Response:
        """Get current simulator state for debugging."""
        return web.json_response({
            "device_state": self.device_state,
            "media_state": self.media_state,
            "device_info": self.device_info,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "timestamp": datetime.now().isoformat()
        })

    async def debug_reset(self, request: Request) -> Response:
        """Reset simulator to initial state."""
        self.device_state.update({
            "power": "on",
            "volume": 20 + (self.device_id * 5),
            "max_volume": 100,
            "mute": False,
            "input": "spotify" if self.device_id == 1 else "bluetooth" if self.device_id == 2 else "hdmi1",
            "sound_program": "stereo"
        })
        
        self.media_state.update({
            "playback": "play" if self.device_id == 1 else "pause" if self.device_id == 2 else "stop",
            "repeat": "off",
            "shuffle": "off",
            "artist": f"MusicCast Artist {self.device_id}",
            "album": f"Test Album {self.device_id}", 
            "track": f"Demo Song {self.device_id}",
            "play_time": 45 + (self.device_id * 10),
            "total_time": 180,
            "albumart_url": f"https://via.placeholder.com/300x300/1a1a1a/ffffff?text=MusicCast+{self.device_id}"
        })
    
        logger.info(f"Device {self.device_id}: Simulator state reset to defaults")
        await self._broadcast_event({
            "type": "state_reset",
            "device_id": self.device_id
        })
        return web.json_response({"message": "State reset to defaults", "response_code": 0})

    async def _broadcast_event(self, event: Dict[str, Any]) -> None:
        """Broadcast event to all WebSocket clients."""
        if not self.websocket_clients:
            return
            
        event["timestamp"] = int(time.time())
        event["device_id"] = self.device_id
        message = json.dumps(event)
        dead_clients = set()
        
        for client in self.websocket_clients:
            try:
                await client.send_str(message)
            except Exception as e:
                logger.warning(f"Device {self.device_id}: Failed to send to WebSocket client: {e}")
                dead_clients.add(client)
        
        # Remove dead clients
        self.websocket_clients -= dead_clients

    def _start_position_update(self):
        """Start position update task."""
        if self._position_task is None:
            self._position_task = asyncio.create_task(self._position_updater())
    
    async def _position_updater(self):
        """Update position when playing."""
        while True:
            try:
                await asyncio.sleep(1)
                if (self.device_state["power"] == "on" and 
                    self.media_state["playback"] == "play"):
                    self.media_state["play_time"] += 1
                    if self.media_state["play_time"] >= self.media_state["total_time"]:
                        # Track ended, go to next
                        await self._change_track()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Device {self.device_id}: Position update error: {e}")

    async def _change_track(self) -> None:
        """Change to a new track."""
        track_num = random.randint(1, 10)
        self.media_state.update({
            "track": f"Track {track_num} - Device {self.device_id}",
            "artist": f"Artist {track_num % 5 + 1} - Device {self.device_id}",
            "album": f"Album {track_num % 3 + 1} - Device {self.device_id}",
            "play_time": 0,
            "total_time": random.randint(120, 300),
            "albumart_url": f"https://via.placeholder.com/300x300/{random.choice(['FF6B35', '1DB954', '0082FC', '4ECDC4'])}/ffffff?text=Track+{track_num}+D{self.device_id}"
        })
        
        await self._broadcast_event({
            "type": "track_change",
            "track": self.media_state["track"],
            "artist": self.media_state["artist"],
            "album": self.media_state["album"],
            "artwork": self.media_state["albumart_url"]
        })

    async def start(self) -> None:
        """Start the simulator server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"MusicCast Simulator {self.device_id} started and bound to {self.host}:{self.port}")
        logger.info(f"Device: {self.device_name} ({self.device_info['device_id']})")
        logger.info(f"Current state: Power {self.device_state['power']}, Playing {self.device_state['input']}")


class MultiDeviceSimulator:
    """Manages multiple MusicCast device simulators."""
    
    def __init__(self):
        self.simulators: List[MusicCastSimulator] = []
        self.base_port = 8080
        self.host = get_local_ip()
    
    async def create_simulators(self, count: int = 3) -> List[Dict[str, Any]]:
        """Create multiple device simulators."""
        device_configs = []
        device_models = ["YAS-209-SIM", "RX-A8A-SIM", "SR-B20A-SIM", "YAS-408-SIM", "MusicCast50-SIM"]
        
        for i in range(count):
            device_id = i + 1
            port = self.base_port + i
            device_model = device_models[i % len(device_models)]
            device_name = f"{device_model}-{device_id}"
            
            simulator = MusicCastSimulator(
                host=self.host,
                port=port,
                device_name=device_name,
                device_id=device_id
            )
            
            # Override device info with specific model
            simulator.device_info["model_name"] = device_model
            simulator.device_info["device_id"] = f"SIM{device_id:06d}"
            
            self.simulators.append(simulator)
            
            device_configs.append({
                "device_id": device_id,
                "name": device_name,
                "model": device_model,
                "ip": self.host,
                "port": port,
                "url": f"http://{self.host}:{port}"
            })
        
        return device_configs
    
    async def start_all(self) -> None:
        """Start all simulators."""
        logger.info(f"Starting {len(self.simulators)} MusicCast device simulators...")
        
        start_tasks = [simulator.start() for simulator in self.simulators]
        await asyncio.gather(*start_tasks)
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎵 Multi-Device MusicCast Simulator Ready")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Use these addresses in the integration setup:")
        for i, simulator in enumerate(self.simulators):
            logger.info(f"  Device {i+1}: {simulator.host}:{simulator.port} ({simulator.device_name})")
        logger.info("")
        logger.info("For multi-device setup:")
        logger.info("  1. Set device count to {}".format(len(self.simulators)))
        logger.info("  2. Use the IP addresses above")
        logger.info("  3. Each device has different content and state")
        logger.info("")
        logger.info("API endpoints for each device:")
        logger.info("  - Device info: http://HOST:PORT/YamahaExtendedControl/v1/system/getDeviceInfo")
        logger.info("  - Status: http://HOST:PORT/YamahaExtendedControl/v1/main/getStatus")
        logger.info("  - Play info: http://HOST:PORT/YamahaExtendedControl/v1/netusb/getPlayInfo")
        logger.info("  - Debug state: http://HOST:PORT/debug/state")
        logger.info("  - Health check: http://HOST:PORT/health")
        logger.info("")


async def main():
    """Main entry point for the multi-device simulator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MusicCast Multi-Device Simulator")
    parser.add_argument("--host", default=None, help="Host to bind to (default: auto-detect local IP)")
    parser.add_argument("--port", type=int, default=8080, help="Base port to bind to (default: 8080)")
    parser.add_argument("--count", type=int, default=3, help="Number of devices to simulate (default: 3)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--single", action="store_true", help="Run single device simulator (legacy mode)")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.single:
        # Legacy single device mode
        host = args.host if args.host else get_local_ip()
        simulator = MusicCastSimulator(host, args.port)
        await simulator.start()
        
        logger.info("")
        logger.info("🎵 Single MusicCast Simulator Started")
        logger.info("=" * 50)
        logger.info("")
        logger.info("Use this address in the integration setup:")
        logger.info(f"  {host}:{args.port}")
        logger.info("")
        logger.info("API endpoints:")
        logger.info(f"  - Device info: http://{host}:{args.port}/YamahaExtendedControl/v1/system/getDeviceInfo")
        logger.info(f"  - Status: http://{host}:{args.port}/YamahaExtendedControl/v1/main/getStatus")
        logger.info(f"  - Play info: http://{host}:{args.port}/YamahaExtendedControl/v1/netusb/getPlayInfo")
        logger.info(f"  - Debug state: http://{host}:{args.port}/debug/state")
        logger.info(f"  - Health check: http://{host}:{args.port}/health")
        logger.info("")
        logger.info("Test commands:")
        logger.info(f"  curl http://{host}:{args.port}/YamahaExtendedControl/v1/system/getDeviceInfo")
        logger.info(f"  curl http://{host}:{args.port}/YamahaExtendedControl/v1/main/getStatus")
        logger.info(f"  curl 'http://{host}:{args.port}/YamahaExtendedControl/v1/main/setPower?power=on'")
        logger.info(f"  curl 'http://{host}:{args.port}/YamahaExtendedControl/v1/netusb/setPlayback?playback=toggle'")
        logger.info("")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("MusicCast Simulator stopped by user")
    else:
        # Multi-device mode
        multi_sim = MultiDeviceSimulator()
        multi_sim.host = args.host if args.host else get_local_ip()
        multi_sim.base_port = args.port
        
        device_configs = await multi_sim.create_simulators(args.count)
        await multi_sim.start_all()
        
        # Show test commands for multi-device
        logger.info("Test commands for each device:")
        for i, config in enumerate(device_configs):
            logger.info(f"  Device {i+1} ({config['name']}):")
            logger.info(f"    curl http://{config['ip']}:{config['port']}/YamahaExtendedControl/v1/system/getDeviceInfo")
            logger.info(f"    curl 'http://{config['ip']}:{config['port']}/YamahaExtendedControl/v1/main/setPower?power=toggle'")
        logger.info("")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Multi-Device MusicCast Simulator stopped by user")


if __name__ == "__main__":
    print("🎵 Yamaha MusicCast Multi-Device Simulator")
    print("=" * 50)
    print("This simulator provides web servers that mimic multiple Yamaha MusicCast APIs")
    print("for testing the Unfolded Circle integration without physical hardware.")
    print("")
    print("Usage:")
    print("  Single device:   python yamaha_simulator.py --single --port 8080")
    print("  Multi-device:    python yamaha_simulator.py --count 3")
    print("  Debug mode:      python yamaha_simulator.py --debug --count 3")
    print("")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulator stopped by user")
    except Exception as e:
        print(f"\nSimulator error: {e}")
        logging.exception("Simulator crashed")