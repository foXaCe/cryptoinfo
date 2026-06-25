"""Shared data management for Cryptoinfo integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .coingecko_api import CoinGeckoAPI
from .storage_helper import DEFAULT_MIN_TIME_BETWEEN_REQUESTS, CryptoInfoStore

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class CryptoInfoData:
    """Manages shared Cryptoinfo data across config entries."""

    __slots__ = ("_hass", "_min_time_between_requests", "api", "store")

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the data manager."""
        self._hass = hass
        self.store = CryptoInfoStore(hass)
        self.api = CoinGeckoAPI(hass)
        self._min_time_between_requests = DEFAULT_MIN_TIME_BETWEEN_REQUESTS

    async def async_initialize(self) -> None:
        """Initialize the data from storage."""
        await self.store.async_load()
        self._min_time_between_requests = self.store.data.get(
            "min_time_between_requests", DEFAULT_MIN_TIME_BETWEEN_REQUESTS
        )

    @property
    def min_time_between_requests(self) -> float:
        """Return minimum time between API requests."""
        return self._min_time_between_requests

    @min_time_between_requests.setter
    def min_time_between_requests(self, value: float) -> None:
        """Set minimum time between API requests."""
        self._min_time_between_requests = value
        self.store.data["min_time_between_requests"] = value
        self._hass.async_create_task(self.store.async_save())
