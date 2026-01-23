"""Diagnostics support for Cryptoinfo."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const.const import (
    CONF_BTC_ADDRESS,
    CryptoInfoConfigEntry,
)

# Keys to redact from diagnostics
TO_REDACT = {
    CONF_BTC_ADDRESS,
    "btc_address",
    "address",
    "api_key",
    "token",
    "password",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: CryptoInfoConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = entry.runtime_data

    # Collect coordinator data
    coordinator_data: dict[str, Any] = {}
    if runtime_data.coordinator:
        coordinator_data["main"] = {
            "last_update_success": runtime_data.coordinator.last_update_success,
            "update_interval": str(runtime_data.coordinator.update_interval),
            "data_keys": list(runtime_data.coordinator.data.keys()) if runtime_data.coordinator.data else [],
        }

    for name, coordinator in runtime_data.coordinators.items():
        coordinator_data[name] = {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "data_available": coordinator.data is not None,
        }

    # Collect shared data info
    shared_data_info = {}
    if runtime_data.shared_data:
        shared_data_info = {
            "min_time_between_requests": runtime_data.shared_data.min_time_between_requests,
        }

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "runtime_data": {
            "shared_data": shared_data_info,
            "coordinators": coordinator_data,
        },
    }
