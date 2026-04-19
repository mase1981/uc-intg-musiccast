"""
MusicCast setup flow.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import RequestUserInput, SetupError, IntegrationSetupError
from ucapi_framework import BaseSetupFlow

from uc_intg_musiccast.client import YamahaMusicCastClient
from uc_intg_musiccast.config import MusicCastConfig

_LOG = logging.getLogger(__name__)


class MusicCastSetupFlow(BaseSetupFlow[MusicCastConfig]):
    """MusicCast setup flow."""

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "MusicCast Device Setup"},
            [
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
                    "field": {"text": {"value": "MusicCast"}},
                },
                {
                    "id": "address",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port"},
                    "field": {"number": {"value": 80, "min": 1, "max": 65535}},
                },
                {
                    "id": "use_ssl",
                    "label": {"en": "Use HTTPS"},
                    "field": {"checkbox": {"value": False}},
                },
                {
                    "id": "info",
                    "label": {"en": "Instructions"},
                    "field": {
                        "label": {
                            "value": {
                                "en": "Enter the IP address of your Yamaha MusicCast device.\n"
                                "Default port is 80 for HTTP. Enable HTTPS if your device uses SSL.\n"
                                "Self-signed certificates are accepted."
                            }
                        }
                    },
                },
            ],
        )

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> MusicCastConfig | RequestUserInput:
        name = input_values.get("name", "MusicCast").strip()
        address = input_values.get("address", "").strip()
        port = int(input_values.get("port", 80))

        use_ssl_value = input_values.get("use_ssl", False)
        if isinstance(use_ssl_value, str):
            use_ssl = use_ssl_value.lower() in ("true", "1", "yes")
        else:
            use_ssl = bool(use_ssl_value)

        if not address:
            raise ValueError("IP Address is required")

        _LOG.info("Testing connection to %s:%d (SSL: %s)", address, port, use_ssl)

        device_info = await YamahaMusicCastClient.verify_device(
            address, port=port, use_ssl=use_ssl
        )
        if not device_info or not device_info.device_id:
            raise ConnectionError(f"Could not connect to MusicCast device at {address}:{port}")

        device_name = name or device_info.friendly_name or "MusicCast"
        identifier = f"musiccast_{address.replace('.', '_')}"

        _LOG.info("Found %s (%s) at %s", device_info.model_name, device_info.device_id, address)

        return MusicCastConfig(
            identifier=identifier,
            name=device_name,
            address=address,
            port=port,
            use_ssl=use_ssl,
        )
