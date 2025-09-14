"""
Configuration management for Yamaha MusicCast Integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

_LOG = logging.getLogger(__name__)


@dataclass
class MusicCastDeviceConfig:
    """Configuration for a single MusicCast device."""
    
    id: str
    name: str
    address: str
    port: int = 80
    enabled: bool = True
    standby_monitoring: bool = True


@dataclass
class MusicCastConfig:
    """Global MusicCast integration configuration."""
    
    devices: Dict[str, MusicCastDeviceConfig] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicCastConfig":
        """Create config from dictionary."""
        devices = {}
        for device_id, device_data in data.get("devices", {}).items():
            devices[device_id] = MusicCastDeviceConfig(
                id=device_id,
                name=device_data.get("name", ""),
                address=device_data.get("address", ""),
                port=device_data.get("port", 80),
                enabled=device_data.get("enabled", True),
                standby_monitoring=device_data.get("standby_monitoring", True)
            )
        
        return cls(devices=devices)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "devices": {
                device_id: {
                    "name": device.name,
                    "address": device.address,
                    "port": device.port,
                    "enabled": device.enabled,
                    "standby_monitoring": device.standby_monitoring
                }
                for device_id, device in self.devices.items()
            }
        }


class Config:
    """Configuration manager for MusicCast integration - Enhanced for multi-device."""

    def __init__(self):
        """Initialize configuration."""
        self._config_dir = os.getenv("UC_CONFIG_HOME")
        if not self._config_dir:
            self._config_dir = os.path.join(os.getcwd(), "config")
        
        self._config_file = os.path.join(self._config_dir, "config.json")
        self._config: Optional[MusicCastConfig] = None
        
        try:
            os.makedirs(self._config_dir, exist_ok=True)
            _LOG.info("Configuration directory: %s", self._config_dir)
        except Exception as e:
            _LOG.error("Failed to create config directory: %s", e)
            self._config_dir = os.getcwd()
            self._config_file = os.path.join(self._config_dir, "config.json")
            _LOG.warning("Using fallback config path: %s", self._config_file)

    @property
    def config(self) -> MusicCastConfig:
        """Get current configuration."""
        if self._config is None:
            self.load()
        return self._config

    def load(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._config = MusicCastConfig.from_dict(data)
                _LOG.info("Configuration loaded successfully from: %s", self._config_file)
            else:
                _LOG.info("No configuration file found at: %s, using defaults", self._config_file)
                self._config = MusicCastConfig()
        except Exception as e:
            _LOG.error("Error loading configuration from %s: %s", self._config_file, e)
            self._config = MusicCastConfig()

    def save(self):
        """Save configuration to file."""
        try:
            os.makedirs(self._config_dir, exist_ok=True)
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            _LOG.info("Configuration saved successfully to: %s", self._config_file)
            _LOG.debug("Saved config data: %s", self._config.to_dict())
        except Exception as e:
            _LOG.error("Error saving configuration to %s: %s", self._config_file, e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value - backward compatibility."""
        if key == "host" and self._config and self._config.devices:
            first_device = next(iter(self._config.devices.values()))
            return first_device.address
        return default

    def set(self, key: str, value: Any):
        """Set configuration value - backward compatibility."""
        if key == "host" and value:
            device_id = f"musiccast_{value.replace('.', '_')}"
            device_config = MusicCastDeviceConfig(
                id=device_id,
                name=f"MusicCast Device ({value})",
                address=value,
                port=80,
                enabled=True,
                standby_monitoring=True
            )
            if self._config is None:
                self._config = MusicCastConfig()
            self._config.devices[device_id] = device_config
            _LOG.debug("Set single device config for host: %s", value)

    def update(self, values: Dict[str, Any]):
        """Update multiple configuration values - backward compatibility."""
        for key, value in values.items():
            self.set(key, value)
        _LOG.debug("Updated config with: %s", values)

    def is_configured(self) -> bool:
        """Check if integration is configured."""
        configured = bool(self._config and self._config.devices)
        _LOG.debug("Is configured check: %s (devices: %d)", configured, len(self._config.devices) if self._config else 0)
        return configured

    def get_host(self) -> Optional[str]:
        """Get configured MusicCast device host - backward compatibility."""
        if self._config and self._config.devices:
            first_device = next(iter(self._config.devices.values()))
            host = first_device.address
            _LOG.debug("Getting host: %s", host)
            return host
        return None

    def add_device(self, device_config: MusicCastDeviceConfig) -> None:
        """Add a device to configuration."""
        if self._config is None:
            self._config = MusicCastConfig()
        self._config.devices[device_config.id] = device_config
        self.save()

    def remove_device(self, device_id: str) -> None:
        """Remove a device from configuration."""
        if self._config and device_id in self._config.devices:
            del self._config.devices[device_id]
            self.save()

    def update_device(self, device_config: MusicCastDeviceConfig) -> None:
        """Update device configuration."""
        if self._config is None:
            self._config = MusicCastConfig()
        self._config.devices[device_config.id] = device_config
        self.save()