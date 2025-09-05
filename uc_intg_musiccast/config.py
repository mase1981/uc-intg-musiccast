"""
Configuration management for Yamaha MusicCast Integration.
Following WiiM pattern.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

_LOG = logging.getLogger(__name__)


class Config:
    """Configuration manager for MusicCast integration - WiiM pattern."""

    def __init__(self):
        """Initialize configuration."""
        # FIXED: Use absolute path and ensure directory exists
        self._config_dir = os.getenv("UC_CONFIG_HOME")
        if not self._config_dir:
            # Default to config subdirectory in current working directory
            self._config_dir = os.path.join(os.getcwd(), "config")
        
        self._config_file = os.path.join(self._config_dir, "config.json")
        self._config: Dict[str, Any] = {}
        
        # CRITICAL: Ensure directory exists before any operations
        try:
            os.makedirs(self._config_dir, exist_ok=True)
            _LOG.info("Configuration directory: %s", self._config_dir)
        except Exception as e:
            _LOG.error("Failed to create config directory: %s", e)
            # Fallback to current directory
            self._config_dir = os.getcwd()
            self._config_file = os.path.join(self._config_dir, "config.json")
            _LOG.warning("Using fallback config path: %s", self._config_file)

    def load(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                _LOG.info("Configuration loaded successfully from: %s", self._config_file)
            else:
                _LOG.info("No configuration file found at: %s, using defaults", self._config_file)
                self._config = {}
        except Exception as e:
            _LOG.error("Error loading configuration from %s: %s", self._config_file, e)
            self._config = {}

    def save(self):
        """Save configuration to file."""
        try:
            # Ensure directory exists before saving
            os.makedirs(self._config_dir, exist_ok=True)
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            _LOG.info("Configuration saved successfully to: %s", self._config_file)
            _LOG.debug("Saved config data: %s", self._config)
        except Exception as e:
            _LOG.error("Error saving configuration to %s: %s", self._config_file, e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value."""
        self._config[key] = value
        _LOG.debug("Set config %s = %s", key, value)

    def update(self, values: Dict[str, Any]):
        """Update multiple configuration values."""
        self._config.update(values)
        _LOG.debug("Updated config with: %s", values)

    def is_configured(self) -> bool:
        """Check if integration is configured."""
        configured = bool(self._config.get("host"))
        _LOG.debug("Is configured check: %s (host: %s)", configured, self._config.get("host"))
        return configured

    def get_host(self) -> Optional[str]:
        """Get configured MusicCast device host."""
        host = self._config.get("host")
        _LOG.debug("Getting host: %s", host)
        return host