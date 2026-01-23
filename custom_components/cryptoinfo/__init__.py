"""Cryptoinfo integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const.const import CryptoInfoRuntimeData
from .exceptions import CryptoInfoConnectionError
from .helper.crypto_info_data import CryptoInfoData

if TYPE_CHECKING:
    from .const.const import CryptoInfoConfigEntry

_LOGGER = logging.getLogger(__name__)

# ConfigEntry version - increment when data schema changes
CONFIG_ENTRY_VERSION = 1
CONFIG_ENTRY_MINOR_VERSION = 0

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version.

    This function handles ConfigEntry migrations when the data schema changes.
    Migrations must be idempotent (safe to run multiple times).

    Version history:
    - 1.0: Initial version (current)
    """
    _LOGGER.debug(
        "Migrating Cryptoinfo config entry from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    # Example migration pattern for future use:
    # if config_entry.version == 1:
    #     new_data = {**config_entry.data}
    #     # Apply migration
    #     new_data["new_key"] = new_data.pop("old_key", "default")
    #     hass.config_entries.async_update_entry(
    #         config_entry,
    #         data=new_data,
    #         version=2,
    #         minor_version=0,
    #     )

    _LOGGER.info(
        "Migration to version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CryptoInfoConfigEntry) -> bool:
    """Set up Cryptoinfo from a config entry."""
    # Initialize shared data (for global settings like min_time_between_requests)
    shared_data = CryptoInfoData(hass)

    try:
        await shared_data.async_initialize()
    except CryptoInfoConnectionError as err:
        raise ConfigEntryNotReady(f"Failed to initialize: {err}") from err

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
