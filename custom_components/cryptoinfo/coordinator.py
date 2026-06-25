"""Data coordinator for Cryptoinfo integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const.const import DOMAIN
from .exceptions import CryptoInfoError, CryptoInfoRateLimitError

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant

    from .helper.coingecko_api import CoinGeckoAPI

_LOGGER = logging.getLogger(__name__)


class CryptoDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for cryptocurrency price data from CoinGecko.

    Fetching is delegated to a shared CoinGeckoAPI client which provides retry,
    rate limiting and a circuit breaker. Sharing a single client across all
    coordinators keeps the global request budget coordinated.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: CoinGeckoAPI,
        cryptocurrency_ids: str,
        currency_name: str,
        update_frequency: timedelta,
        id_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{id_name or 'default'}",
            update_interval=update_frequency,
        )
        self.api = api
        self.cryptocurrency_ids = cryptocurrency_ids
        self.currency_name = currency_name
        self.id_name = id_name

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch market data from CoinGecko via the shared resilient client."""
        try:
            data = await self.api.get_coins_markets(self.cryptocurrency_ids, self.currency_name)
        except CryptoInfoRateLimitError as err:
            raise UpdateFailed(f"Rate limited by CoinGecko: {err}") from err
        except CryptoInfoError as err:
            raise UpdateFailed(f"Error fetching data from CoinGecko: {err}") from err

        return {coin["id"]: coin for coin in data if isinstance(coin, dict) and "id" in coin}
