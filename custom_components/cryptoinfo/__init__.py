"""Cryptoinfo integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const.const import CryptoInfoRuntimeData
from .helper.crypto_info_data import CryptoInfoData

if TYPE_CHECKING:
    from .const.const import CryptoInfoConfigEntry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: CryptoInfoConfigEntry) -> bool:
    """Set up Cryptoinfo from a config entry."""
    # Initialize shared data (for global settings like min_time_between_requests)
    shared_data = CryptoInfoData(hass)
    await shared_data.async_initialize()

    # Store runtime data on the entry (Platinum pattern)
    entry.runtime_data = CryptoInfoRuntimeData(
        shared_data=shared_data,
        coordinator=None,
        coordinators={},
    )

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for reconfiguration
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.debug("Cryptoinfo entry %s set up successfully", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CryptoInfoConfigEntry) -> bool:
    """Unload a config entry."""
    # Save shared data before unloading
    if entry.runtime_data and entry.runtime_data.shared_data:
        await entry.runtime_data.shared_data.store.async_save()

    # Unload platforms
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: CryptoInfoConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
