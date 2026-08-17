"""Storage helper for CryptoInfo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

STORAGE_VERSION = 1
STORAGE_KEY = "cryptoinfo_data"

# Default minimum delay (minutes) between CoinGecko API requests, shared by all sensors.
DEFAULT_MIN_TIME_BETWEEN_REQUESTS = 0.25


class CryptoInfoStore:
    """Class to hold CryptoInfo data."""

    __slots__ = ("data", "hass", "store")

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self.hass = hass
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {"min_time_between_requests": DEFAULT_MIN_TIME_BETWEEN_REQUESTS}

    async def async_load(self) -> None:
        """Load the data from storage."""
        stored = await self.store.async_load()
        if stored:
            self.data = stored

    async def async_save(self) -> None:
        """Save data to storage."""
        await self.store.async_save(self.data)
