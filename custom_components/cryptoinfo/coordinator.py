"""Data coordinators for Cryptoinfo integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const.const import API_ENDPOINT, DOMAIN
from .exceptions import CryptoInfoApiError

_LOGGER = logging.getLogger(__name__)

# Default timeout for API requests (seconds)
DEFAULT_TIMEOUT = 30


class CryptoDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for cryptocurrency price data from CoinGecko."""

    _active_coordinators: set[int] = set()
    _instance_count: int = 0
    _last_update_time: datetime | None = None
    _last_updated_id: int | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        cryptocurrency_ids: str,
        currency_name: str,
        update_frequency: timedelta,
        min_time_between_requests: timedelta,
        id_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{id_name or 'default'}",
            update_interval=update_frequency,
        )
        self.instance_id = CryptoDataCoordinator._instance_count
        CryptoDataCoordinator._instance_count += 1
        CryptoDataCoordinator._active_coordinators.add(self.instance_id)

        self.cryptocurrency_ids = cryptocurrency_ids
        self.currency_name = currency_name
        self.id_name = id_name
        self.min_time_between_requests = min_time_between_requests
        self.update_frequency = update_frequency

    async def async_shutdown(self) -> None:
        """Handle coordinator shutdown."""
        _LOGGER.debug("Shutting down coordinator %s", self.instance_id)
        CryptoDataCoordinator._active_coordinators.discard(self.instance_id)
        if CryptoDataCoordinator._last_updated_id == self.instance_id:
            CryptoDataCoordinator._last_updated_id = None
        await super().async_shutdown()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from CoinGecko API with coordinated timing."""
        current_time = datetime.now()

        # First request: fetch immediately
        if CryptoDataCoordinator._last_update_time is None:
            return await self._fetch_data(current_time)

        # Check if enough time has passed
        time_since_last = current_time - CryptoDataCoordinator._last_update_time
        if time_since_last + timedelta(seconds=1) < self.min_time_between_requests:
            _LOGGER.debug(
                "Coordinator %s waiting: %s since last request (min: %s)",
                self.instance_id,
                time_since_last,
                self.min_time_between_requests,
            )
            return self.data or {}

        # Check if it's our turn
        if not self._is_our_turn():
            _LOGGER.debug("Coordinator %s waiting for turn", self.instance_id)
            return self.data or {}

        return await self._fetch_data(current_time)

    def _is_our_turn(self) -> bool:
        """Check if this coordinator should update now."""
        last_id = CryptoDataCoordinator._last_updated_id
        active_ids = sorted(CryptoDataCoordinator._active_coordinators)

        if not active_ids:
            return True

        if last_id is None or last_id not in CryptoDataCoordinator._active_coordinators:
            return self.instance_id == min(active_ids)

        current_index = active_ids.index(last_id)
        next_index = (current_index + 1) % len(active_ids)
        return self.instance_id == active_ids[next_index]

    async def _fetch_data(self, current_time: datetime) -> dict[str, Any]:
        """Fetch data from the API."""
        url = (
            f"{API_ENDPOINT}coins/markets"
            f"?ids={self.cryptocurrency_ids}"
            f"&vs_currency={self.currency_name}"
            f"&price_change_percentage=1h%2C24h%2C7d%2C14d%2C30d%2C1y"
        )

        _LOGGER.debug(
            "Fetching data for %s (coordinator %s)",
            self.cryptocurrency_ids,
            self.instance_id,
        )

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with session.get(url) as response:
                    if response.status == 429:
                        raise CryptoInfoApiError("Rate limited by CoinGecko API")
                    response.raise_for_status()
                    data = await response.json()

                    # Update timing after successful request
                    CryptoDataCoordinator._last_update_time = current_time
                    CryptoDataCoordinator._last_updated_id = self.instance_id

                    return {coin["id"]: coin for coin in data}

        except TimeoutError as err:
            _LOGGER.warning("Timeout fetching crypto data from CoinGecko")
            raise UpdateFailed("Request timeout") from err
        except CryptoInfoApiError:
            raise
        except Exception as err:
            _LOGGER.error("Error fetching crypto data: %s", err)
            raise UpdateFailed(f"Error fetching data: {err}") from err
