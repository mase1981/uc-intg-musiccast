"""
Yamaha MusicCast Integration Driver for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import List, Optional
from aiohttp import web

import ucapi
from ucapi import DeviceStates, Events, IntegrationSetupError, SetupComplete, SetupError

from uc_intg_musiccast.client import YamahaMusicCastClient
from uc_intg_musiccast.config import Config
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
client: Optional[YamahaMusicCastClient] = None
update_task: Optional[asyncio.Task] = None
media_player_entity: Optional[YamahaMusicCastMediaPlayer] = None
remote_entity: Optional[MusicCastRemote] = None

entities_ready = False
initialization_lock = asyncio.Lock()

async def _initialize_integration():
    """
    CRITICAL: Initialize integration and create entities atomically.
    This prevents race conditions between UC Remote subscription and entity creation.
    """
    global client, api, config, update_task, media_player_entity, remote_entity, entities_ready
    
    async with initialization_lock:
        if entities_ready:
            _LOG.debug("Entities already initialized, skipping")
            return True
            
        if not config or not config.is_configured():
            _LOG.error("Configuration not found or invalid.")
            if api: 
                await api.set_device_state(DeviceStates.ERROR)
            return False

        _LOG.info("Initializing MusicCast integration...")
        if api: 
            await api.set_device_state(DeviceStates.CONNECTING)

        try:
            host = config.get_host()
            client = YamahaMusicCastClient(host)
            device_info = await client.get_device_info()

            device_name = device_info.friendly_name or 'MusicCast Device'
            device_id = device_info.device_id or 'MUSICCAST_DEVICE'

            _LOG.info("Connected to MusicCast device: %s (ID: %s)", device_name, device_id)

            _LOG.info("Creating entities...")
            
            # Create entities
            media_player_entity = YamahaMusicCastMediaPlayer(device_id, device_name)
            remote_entity = MusicCastRemote(device_id, device_name)

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

            entities_ready = True
            
            # Start update task
            if update_task:
                update_task.cancel()
            update_task = asyncio.create_task(periodic_update())

            await api.set_device_state(DeviceStates.CONNECTED)
            _LOG.info("MusicCast integration initialization completed successfully.")
            return True

        except Exception as e:
            _LOG.error("Initialization failed: %s", e, exc_info=True)
            entities_ready = False  # CRITICAL: Don't mark ready on failure
            if api: 
                await api.set_device_state(DeviceStates.ERROR)
            return False

async def setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Handle driver setup requests."""
    global config

    if isinstance(msg, ucapi.DriverSetupRequest):
        host = msg.setup_data.get("host")
        if not host:
            _LOG.error("No host provided in setup data")
            return SetupError(IntegrationSetupError.OTHER)

        _LOG.info("Testing connection to MusicCast device at %s", host)
        try:
            async with YamahaMusicCastClient(host) as test_client:
                device_info = await test_client.get_device_info()
                if not device_info or not device_info.device_id:
                     _LOG.error("Connection test failed for host: %s", host)
                     return SetupError(IntegrationSetupError.CONNECTION_REFUSED)

            config.set("host", host)
            config.save()

            asyncio.create_task(_initialize_integration())
            return SetupComplete()

        except Exception as e:
            _LOG.error("Setup error: %s", e)
            return SetupError(IntegrationSetupError.OTHER)

    return SetupComplete()

async def periodic_update():
    """Periodically update entity states."""
    _LOG.info("Starting periodic update task.")
    while True:
        try:
            await asyncio.sleep(5.0)
            if (api and api.device_state == DeviceStates.CONNECTED and
                media_player_entity and remote_entity and client and entities_ready):
                await media_player_entity.update_attributes()
                await remote_entity.update_attributes()
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
    
    # Proceed with subscription logic
    if media_player_entity and media_player_entity.id in entity_ids:
        await media_player_entity.update_attributes()
    if remote_entity and remote_entity.id in entity_ids:
        await remote_entity.update_attributes()

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

        # Set initial state based on configuration
        if not config.is_configured():
            _LOG.info("Device not configured, waiting for setup...")
            await api.set_device_state(DeviceStates.DISCONNECTED)

        await asyncio.Future()
        
    except Exception as e:
        _LOG.critical("Fatal error in main: %s", e, exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())