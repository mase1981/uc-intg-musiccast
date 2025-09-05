"""
Setup flow implementation for Yamaha MusicCast Integration.

Handles device discovery, user confirmation, and configuration validation
during the integration setup process.

:copyright: (c) 2025 by Meir Miyara
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from ucapi import (
    SetupDriver,
    DriverSetupRequest,
    UserDataResponse,
    UserConfirmationResponse,
    AbortDriverSetup,
    SetupAction,
    RequestUserInput,
    RequestUserConfirmation,
    SetupComplete,
    SetupError,
    IntegrationSetupError
)

from uc_intg_musiccast.client import YamahaMusicCastClient, DeviceInfo
from uc_intg_musiccast.config import Config

_LOG = logging.getLogger(__name__)


class YamahaMusicCastSetup:
    """
    Handles the setup flow for Yamaha MusicCast integration.
    
    Supports both automatic device discovery and manual IP configuration
    with proper user feedback and error handling.
    """
    
    def __init__(self):
        """Initialize setup handler."""
        self.discovered_devices: List[tuple[str, DeviceInfo]] = []
        self.selected_device: Optional[tuple[str, DeviceInfo]] = None
        self.setup_data: Dict[str, Any] = {}
        self.current_step = "initial"
    
    async def handle_setup(self, msg: SetupDriver) -> SetupAction:
        """
        Handle setup message from Remote Two.
        
        :param msg: Setup message
        :return: Setup action response
        """
        try:
            if isinstance(msg, DriverSetupRequest):
                return await self._handle_setup_request(msg)
            elif isinstance(msg, UserDataResponse):
                return await self._handle_user_data(msg)
            elif isinstance(msg, UserConfirmationResponse):
                return await self._handle_user_confirmation(msg)
            elif isinstance(msg, AbortDriverSetup):
                return await self._handle_abort(msg)
            else:
                _LOG.error(f"Unsupported setup message type: {type(msg)}")
                return SetupError(IntegrationSetupError.OTHER)
                
        except Exception as e:
            _LOG.error(f"Setup error: {e}", exc_info=True)
            return SetupError(IntegrationSetupError.OTHER)
    
    async def _handle_setup_request(self, msg: DriverSetupRequest) -> SetupAction:
        """Handle initial setup request."""
        _LOG.info("Starting Yamaha MusicCast setup")
        
        # Store setup data
        self.setup_data = msg.setup_data
        discovery_mode = self.setup_data.get("device_discovery", "auto")
        
        if discovery_mode == "auto":
            self.current_step = "discovery"
            return await self._start_device_discovery()
        else:
            self.current_step = "manual_ip"
            return await self._request_manual_ip()
    
    async def _start_device_discovery(self) -> SetupAction:
        """Start automatic device discovery."""
        _LOG.info("Starting automatic device discovery...")
        
        try:
            # Discover devices with reasonable timeout
            self.discovered_devices = await YamahaMusicCastClient.discover_devices(timeout=10)
            
            if not self.discovered_devices:
                # No devices found, offer manual configuration
                return RequestUserConfirmation(
                    title={
                        "en": "No Devices Found",
                        "de": "Keine Geräte gefunden"
                    },
                    header={
                        "en": "Automatic Discovery Failed",
                        "de": "Automatische Erkennung fehlgeschlagen"
                    },
                    footer={
                        "en": "No Yamaha MusicCast devices were found on your network. Would you like to configure a device manually?",
                        "de": "Es wurden keine Yamaha MusicCast-Geräte in Ihrem Netzwerk gefunden. Möchten Sie ein Gerät manuell konfigurieren?"
                    }
                )
            elif len(self.discovered_devices) == 1:
                # Single device found, auto-select it
                self.selected_device = self.discovered_devices[0]
                return await self._confirm_device_selection()
            else:
                # Multiple devices found, let user choose
                return await self._request_device_selection()
                
        except Exception as e:
            _LOG.error(f"Discovery failed: {e}")
            return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
    
    async def _request_device_selection(self) -> SetupAction:
        """Request user to select from discovered devices."""
        self.current_step = "device_selection"
        
        # Create device selection dropdown
        device_items = []
        for i, (ip, device_info) in enumerate(self.discovered_devices):
            device_items.append({
                "id": str(i),
                "label": {
                    "en": f"{device_info.model_name} ({ip})",
                    "de": f"{device_info.model_name} ({ip})"
                }
            })
        
        settings = [
            {
                "id": "selected_device",
                "label": {
                    "en": "Select Device",
                    "de": "Gerät auswählen"
                },
                "field": {
                    "dropdown": {
                        "value": "0",
                        "items": device_items
                    }
                }
            }
        ]
        
        return RequestUserInput(
            title={
                "en": "Select MusicCast Device",
                "de": "MusicCast-Gerät auswählen"
            },
            settings=settings
        )
    
    async def _request_manual_ip(self) -> SetupAction:
        """Request manual IP configuration."""
        self.current_step = "manual_ip"
        
        settings = [
            {
                "id": "device_ip",
                "label": {
                    "en": "Device IP Address",
                    "de": "Geräte-IP-Adresse"
                },
                "field": {
                    "text": {
                        "value": self.setup_data.get("device_ip", ""),
                        "regex": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
                    }
                }
            },
            {
                "id": "device_name",
                "label": {
                    "en": "Device Name (Optional)",
                    "de": "Gerätename (Optional)"
                },
                "field": {
                    "text": {
                        "value": self.setup_data.get("device_name", "")
                    }
                }
            }
        ]
        
        return RequestUserInput(
            title={
                "en": "Manual Device Configuration",
                "de": "Manuelle Gerätekonfiguration"
            },
            settings=settings
        )
    
    async def _confirm_device_selection(self) -> SetupAction:
        """Confirm selected device configuration."""
        if not self.selected_device:
            return SetupError(IntegrationSetupError.OTHER)
        
        ip, device_info = self.selected_device
        
        return RequestUserConfirmation(
            title="Confirm Device Setup",
            header=f"Found: {device_info.model_name}",
            footer=f"IP Address: {ip}\nDevice ID: {device_info.device_id}\nSystem Version: {device_info.system_version}\n\nPress Continue to complete setup."
        )
    
    async def _handle_user_data(self, msg: UserDataResponse) -> SetupAction:
        """Handle user input data."""
        input_values = msg.input_values
        
        if self.current_step == "device_selection":
            # User selected a device from discovered list
            try:
                selected_index = int(input_values.get("selected_device", "0"))
                if 0 <= selected_index < len(self.discovered_devices):
                    self.selected_device = self.discovered_devices[selected_index]
                    return await self._confirm_device_selection()
                else:
                    return SetupError(IntegrationSetupError.OTHER)
            except (ValueError, IndexError):
                return SetupError(IntegrationSetupError.OTHER)
        
        elif self.current_step == "manual_ip":
            # User provided manual IP configuration
            device_ip = input_values.get("device_ip", "").strip()
            if not device_ip:
                return SetupError(IntegrationSetupError.OTHER)
            
            # Verify device at provided IP
            device_info = await YamahaMusicCastClient.verify_device(device_ip, timeout=5)
            if not device_info:
                return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
            
            # Use custom name if provided
            custom_name = input_values.get("device_name", "").strip()
            if custom_name:
                device_info.friendly_name = custom_name
            
            self.selected_device = (device_ip, device_info)
            return await self._confirm_device_selection()
        
        return SetupError(IntegrationSetupError.OTHER)
    
    async def _handle_user_confirmation(self, msg: UserConfirmationResponse) -> SetupAction:
        """Handle user confirmation."""
        if not msg.confirm:
            return SetupError(IntegrationSetupError.OTHER)
        
        if self.current_step == "discovery" and not self.discovered_devices:
            # User wants manual configuration after failed discovery
            return await self._request_manual_ip()
        
        # User confirmed device selection, complete setup
        return await self._complete_setup()
    
    async def _complete_setup(self) -> SetupAction:
        """Complete the setup process."""
        if not self.selected_device:
            return SetupError(IntegrationSetupError.OTHER)
        
        ip, device_info = self.selected_device
        
        try:
            # Final device test
            async with YamahaMusicCastClient(ip, timeout=5) as client:
                await client.get_status()  # Test basic connectivity
            
            # Update setup data with device information
            self.setup_data.update({
                "device_ip": ip,
                "device_name": device_info.friendly_name,
                "device_id": device_info.device_id,
                "model_name": device_info.model_name
            })
            
            _LOG.info(f"Setup completed for {device_info.model_name} at {ip}")
            return SetupComplete()
            
        except Exception as e:
            _LOG.error(f"Final device test failed: {e}")
            return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
    
    async def _handle_abort(self, msg: AbortDriverSetup) -> SetupAction:
        """Handle setup abortion."""
        _LOG.info(f"Setup aborted: {msg.error}")
        return SetupError(msg.error)
    
    def get_config_data(self) -> Dict[str, Any]:
        """Get configuration data for saving."""
        return self.setup_data


async def setup_handler(msg: SetupDriver) -> SetupAction:
    """
    Global setup handler function.
    
    :param msg: Setup message
    :return: Setup action response
    """
    # Create setup instance for this session
    if not hasattr(setup_handler, '_setup_instance'):
        setup_handler._setup_instance = YamahaMusicCastSetup()
    
    return await setup_handler._setup_instance.handle_setup(msg)


def get_setup_data() -> Dict[str, Any]:
    """Get setup data from current setup session."""
    if hasattr(setup_handler, '_setup_instance'):
        return setup_handler._setup_instance.get_config_data()
    return {}


def clear_setup_session():
    """Clear current setup session."""
    if hasattr(setup_handler, '_setup_instance'):
        delattr(setup_handler, '_setup_instance')