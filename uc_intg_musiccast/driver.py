"""
Yamaha MusicCast Integration Driver for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from aiohttp import web

import ucapi
from ucapi import DeviceStates, Events, IntegrationSetupError, SetupComplete, SetupError, RequestUserInput, UserDataResponse

from uc_intg_musiccast.client import YamahaMusicCastClient
from uc_intg_musiccast.config import Config, MusicCastDeviceConfig
from uc_intg_musiccast.media_player import YamahaMusicCastMediaPlayer
from uc_intg_musiccast.remote import MusicCastRemote

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOG = logging.getLogger(__name__)

# Globals
api: Optional[ucapi.IntegrationAPI] = None
config: Optional[Config] = None
clients: Dict[str, YamahaMusicCastClient] = {}
media_players: Dict[str, YamahaMusicCastMediaPlayer] = {}
remotes: Dict[str, MusicCastRemote] = {}

entities_ready = False
initialization_lock = asyncio.Lock()

# Multi-device setup state
setup_state = {"step": "initial", "device_count": 1, "devices_data": []}

async def _initialize_integration():
    """
    CRITICAL: Initialize integration and create entities atomically.
    Enhanced for multi-device support with port and SSL configuration.
    """
    global clients, api, config, media_players, remotes, entities_ready
    
    async with initialization_lock:
        if entities_ready:
            _LOG.debug("Entities already initialized, skipping")
            return True
            
        if not config or not config.is_configured():
            _LOG.error("Configuration not found or invalid.")
            if api: 
                await api.set_device_state(DeviceStates.ERROR)
            return False

        _LOG.info("Initializing MusicCast integration for %d devices...", len(config.config.devices))
        if api: 
            await api.set_device_state(DeviceStates.CONNECTING)

        connected_devices = 0

        for device_id, device_config in config.config.devices.items():
            if not device_config.enabled:
                _LOG.info("Skipping disabled device: %s", device_config.name)
                continue

            try:
                _LOG.info("Connecting to MusicCast device: %s at %s:%d (SSL: %s)", 
                         device_config.name, device_config.address, 
                         device_config.port, device_config.use_ssl)
                
                # Create client with port and SSL settings
                client = YamahaMusicCastClient(
                    device_config.address,
                    port=device_config.port,
                    use_ssl=device_config.use_ssl
                )
                device_info = await client.get_device_info()

                device_name = device_config.name or device_info.friendly_name or 'MusicCast Device'
                device_entity_id = device_info.device_id or f'MUSICCAST_{device_id}'

                _LOG.info("Connected to MusicCast device: %s (ID: %s)", device_name, device_entity_id)

                # Create entities with unique IDs for multi-device support
                media_player_id = f"musiccast_{device_id}_media_player"
                remote_id = f"musiccast_{device_id}_remote"

                # Create entities
                media_player_entity = YamahaMusicCastMediaPlayer(media_player_id, device_name)
                remote_entity = MusicCastRemote(remote_id, device_name)

                # Set client for both entities
                media_player_entity.set_client(client)
                remote_entity.set_client(client)

                # Link API to entities
                media_player_entity._integration_api = api
                remote_entity._integration_api = api

                # Add entities to available BEFORE marking ready
                api.available_entities.add(media_player_entity)
                api.available_entities.add(remote_entity)
                api.configured_entities.add(media_player_entity)
                api.configured_entities.add(remote_entity)

                # Initialize sources and capabilities
                await media_player_entity.initialize_sources()
                await remote_entity.initialize_capabilities()
                await media_player_entity.update_attributes()

                # Store references
                clients[device_id] = client
                media_players[device_id] = media_player_entity
                remotes[device_id] = remote_entity

                connected_devices += 1
                _LOG.info("Successfully setup device: %s", device_config.name)

            except Exception as e:
                _LOG.error("Failed to setup device %s: %s", device_config.name, e, exc_info=True)
                continue

        if connected_devices > 0:
            entities_ready = True
            await api.set_device_state(DeviceStates.CONNECTED)
            _LOG.info("MusicCast integration initialization completed successfully - %d/%d devices connected.", connected_devices, len(config.config.devices))
            return True
        else:
            entities_ready = False
            if api: 
                await api.set_device_state(DeviceStates.ERROR)
            _LOG.error("No devices could be connected during initialization")
            return False

async def setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Enhanced setup handler for multi-device support with port and SSL configuration."""
    global config, entities_ready, setup_state

    if isinstance(msg, ucapi.DriverSetupRequest):
        # Initial setup - check if single or multi-device
        device_count = int(msg.setup_data.get("device_count", 1))
        
        if device_count == 1:
            # Single device - use enhanced flow with port and SSL
            return await _handle_single_device_setup(msg.setup_data)
        else:
            # Multi-device setup
            setup_state = {"step": "collect_ips", "device_count": device_count, "devices_data": []}
            return await _request_device_ips(device_count)
    
    elif isinstance(msg, UserDataResponse):
        if setup_state["step"] == "collect_ips":
            return await _handle_device_ips_collection(msg.input_values)
        else:
            # Handle single device detailed config
            return await _handle_single_device_setup(msg.input_values)

    return SetupError(IntegrationSetupError.OTHER)

async def _handle_single_device_setup(setup_data: Dict[str, Any]) -> ucapi.SetupAction:
    """Handle single device setup with port and SSL support."""
    
    # Check if we need to request detailed config
    if "port" not in setup_data or "use_ssl" not in setup_data:
        host = setup_data.get("host", "")
        return ucapi.RequestUserInput(
            title={"en": "Device Configuration"},
            settings=[
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": host}}
                },
                {
                    "id": "port",
                    "label": {"en": "Port"},
                    "field": {"number": {"value": 80, "min": 1, "max": 65535}}
                },
                {
                    "id": "use_ssl",
                    "label": {"en": "Use HTTPS (ignore self-signed certificates)"},
                    "field": {"checkbox": {"value": False}}
                }
            ]
        )
    
    host = setup_data.get("host")
    port = int(setup_data.get("port", 80))
    
    # Properly convert string "true"/"false" to boolean
    use_ssl_value = setup_data.get("use_ssl", False)
    if isinstance(use_ssl_value, str):
        use_ssl = use_ssl_value.lower() in ("true", "1", "yes")
    else:
        use_ssl = bool(use_ssl_value)
    
    if not host:
        _LOG.error("No host provided in setup data")
        return SetupError(IntegrationSetupError.OTHER)

    _LOG.info(f"Testing connection to MusicCast device at {host}:{port} (SSL: {use_ssl})")
    try:
        async with YamahaMusicCastClient(host, port=port, use_ssl=use_ssl) as test_client:
            device_info = await test_client.get_device_info()
            if not device_info or not device_info.device_id:
                 _LOG.error(f"Connection test failed for host: {host}:{port}")
                 return SetupError(IntegrationSetupError.CONNECTION_REFUSED)

        # Create device configuration
        device_id = f"musiccast_{host.replace('.', '_')}"
        device_config = MusicCastDeviceConfig(
            id=device_id,
            name=device_info.friendly_name or f"MusicCast Device ({host})",
            address=host,
            port=port,
            use_ssl=use_ssl,
            enabled=True,
            standby_monitoring=True
        )

        config.add_device(device_config)
        
        # Initialize entities immediately after setup
        asyncio.create_task(_initialize_integration())
        return SetupComplete()

    except Exception as e:
        _LOG.error("Setup error: %s", e)
        return SetupError(IntegrationSetupError.OTHER)

async def _request_device_ips(device_count: int) -> RequestUserInput:
    """Request IP addresses for multiple devices with port and SSL support."""
    settings = []
    
    for i in range(device_count):
        settings.extend([
            {
                "id": f"device_{i}_ip",
                "label": {"en": f"Device {i+1} IP Address"},
                "description": {"en": f"IP address for MusicCast device {i+1} (e.g., 192.168.1.{100+i})"},
                "field": {"text": {"value": f"192.168.1.{100+i}"}}
            },
            {
                "id": f"device_{i}_port",
                "label": {"en": f"Device {i+1} Port"},
                "description": {"en": "Default: 80 for HTTP, 443 for HTTPS"},
                "field": {"number": {"value": 80, "min": 1, "max": 65535}}
            },
            {
                "id": f"device_{i}_ssl",
                "label": {"en": f"Device {i+1} Use HTTPS"},
                "description": {"en": "Enable for HTTPS (ignores self-signed certificate warnings)"},
                "field": {"checkbox": {"value": False}}
            },
            {
                "id": f"device_{i}_name", 
                "label": {"en": f"Device {i+1} Name"},
                "description": {"en": f"Friendly name for device {i+1}"},
                "field": {"text": {"value": f"MusicCast Device {i+1}"}}
            }
        ])
    
    return RequestUserInput(
        title={"en": f"Configure {device_count} MusicCast Devices"},
        settings=settings
    )

async def _handle_device_ips_collection(input_values: Dict[str, Any]) -> ucapi.SetupAction:
    """Process multiple device IPs with port and SSL configuration."""
    devices_to_test = []
    
    # Extract device data from input
    device_index = 0
    while f"device_{device_index}_ip" in input_values:
        ip_input = input_values[f"device_{device_index}_ip"]
        port = int(input_values.get(f"device_{device_index}_port", 80))
        
        # Properly convert string "true"/"false" to boolean
        use_ssl_value = input_values.get(f"device_{device_index}_ssl", False)
        if isinstance(use_ssl_value, str):
            use_ssl = use_ssl_value.lower() in ("true", "1", "yes")
        else:
            use_ssl = bool(use_ssl_value)
        
        name = input_values[f"device_{device_index}_name"]
        
        devices_to_test.append({
            "host": ip_input.strip(),
            "port": port,
            "use_ssl": use_ssl,
            "name": name.strip(),
            "index": device_index
        })
        device_index += 1
    
    # Test all devices concurrently
    _LOG.info(f"Testing connections to {len(devices_to_test)} devices...")
    test_results = await _test_multiple_devices(devices_to_test)
    
    # Process results and save successful configurations
    successful_devices = 0
    for device_data, success in zip(devices_to_test, test_results):
        if success:
            device_id = f"musiccast_{device_data['host'].replace('.', '_')}"
            device_config = MusicCastDeviceConfig(
                id=device_id,
                name=device_data['name'],
                address=device_data['host'],
                port=device_data['port'],
                use_ssl=device_data['use_ssl'],
                enabled=True,
                standby_monitoring=True
            )
            config.add_device(device_config)
            successful_devices += 1
            _LOG.info(f"✅ Device {device_data['index'] + 1} ({device_data['name']}) connection successful")
        else:
            _LOG.error(f"❌ Device {device_data['index'] + 1} ({device_data['name']}) connection failed")
    
    if successful_devices == 0:
        _LOG.error("No devices could be connected")
        return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
    
    # Initialize all entities
    await _initialize_integration()
    _LOG.info(f"Multi-device setup completed: {successful_devices}/{len(devices_to_test)} devices configured")
    return SetupComplete()

async def _test_multiple_devices(devices: List[Dict]) -> List[bool]:
    """Test connections to multiple devices concurrently with port and SSL support."""
    async def test_device(device_data):
        try:
            async with YamahaMusicCastClient(
                device_data['host'], 
                port=device_data['port'],
                use_ssl=device_data['use_ssl']
            ) as client:
                device_info = await client.get_device_info()
                if device_info:
                    _LOG.info(f"Device {device_data['index'] + 1}: {device_info.model_name} ({device_info.device_id})")
                    return True
                return False
        except Exception as e:
            _LOG.error(f"Device {device_data['index'] + 1} test error: {e}")
            return False
    
    tasks = [test_device(device) for device in devices]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to False
    return [result if isinstance(result, bool) else False for result in results]

async def periodic_update():
    """Periodically update entity states for all devices."""
    _LOG.info("Starting periodic update task.")
    while True:
        try:
            await asyncio.sleep(5.0)
            if (api and api.device_state == DeviceStates.CONNECTED and
                media_players and remotes and entities_ready):
                for device_id in media_players:
                    media_player = media_players.get(device_id)
                    remote = remotes.get(device_id)
                    if media_player and remote:
                        await media_player.update_attributes()
                        await remote.update_attributes()
        except asyncio.CancelledError:
            _LOG.info("Periodic update task cancelled.")
            break
        except Exception as e:
            _LOG.error("Error in periodic update: %s", e)

async def on_subscribe_entities(entity_ids: List[str]):
    """Handle entity subscription events."""
    _LOG.info("Entities subscribed: %s", entity_ids)
    
    if not entities_ready:
        _LOG.error("RACE CONDITION: Subscription before entities ready!")
        success = await _initialize_integration()
        if not success:
            _LOG.error("Failed to initialize during subscription attempt")
            return
    
    # Proceed with subscription logic for all devices
    for entity_id in entity_ids:
        for device_id, media_player in media_players.items():
            if media_player.id == entity_id:
                await media_player.update_attributes()
                break
        for device_id, remote in remotes.items():
            if remote.id == entity_id:
                await remote.update_attributes()
                break

async def on_connect():
    """Handle UC Remote connection."""
    global entities_ready
    
    _LOG.info("Remote Two connected")
    
    if config and config.is_configured():
        if not entities_ready:
            _LOG.warning("Entities not ready on connect - initializing now")
            await _initialize_integration()
        else:
            _LOG.info("Entities already ready, confirming connection")
            if api:
                await api.set_device_state(DeviceStates.CONNECTED)
    else:
        _LOG.info("Not configured, waiting for setup")
        if api:
            await api.set_device_state(DeviceStates.DISCONNECTED)

async def on_disconnect():
    """Handle UC Remote disconnection."""
    _LOG.info("Remote Two disconnected")

async def on_unsubscribe_entities(entity_ids: List[str]):
    """Handle entity unsubscription events."""
    _LOG.info("Entities unsubscribed: %s", entity_ids)

async def health_check(request):
    """Simple health check endpoint for Docker."""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Start health check server for Docker."""
    try:
        app = web.Application()
        app.router.add_get('/health', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 9090)
        await site.start()
        _LOG.info("Health check server started on port 9090")
    except Exception as e:
        _LOG.error("Failed to start health server: %s", e)

async def main():
    """Main driver entry point."""
    global api, config
    
    _LOG.info("Starting MusicCast Integration Driver")
    try:
        loop = asyncio.get_running_loop()
        config = Config()
        config.load()

        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        api = ucapi.IntegrationAPI(loop)

        if config.is_configured():
            _LOG.info("Pre-configuring entities before UC Remote connection")
            asyncio.create_task(_initialize_integration())

        # Initialize API after starting entity creation
        await api.init(os.path.abspath(driver_path), setup_handler)

        # Start health server for Docker
        asyncio.create_task(start_health_server())

        # Add event listeners
        api.add_listener(Events.SUBSCRIBE_ENTITIES, on_subscribe_entities)
        api.add_listener(Events.UNSUBSCRIBE_ENTITIES, on_unsubscribe_entities)
        api.add_listener(Events.CONNECT, on_connect)
        api.add_listener(Events.DISCONNECT, on_disconnect)

        # Start periodic update task
        asyncio.create_task(periodic_update())

        # Set initial state based on configuration
        if not config.is_configured():
            _LOG.info("Device not configured, waiting for setup...")
            await api.set_device_state(DeviceStates.DISCONNECTED)

        await asyncio.Future()
        
    except Exception as e:
        _LOG.critical("Fatal error in main: %s", e, exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())