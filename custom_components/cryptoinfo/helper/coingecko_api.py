#!/usr/bin/env python3
"""
CoinGecko API helper for Cryptoinfo
Author: Johnny Visser
"""

from homeassistant.helpers import aiohttp_client
from ..const.const import API_ENDPOINT, _LOGGER


class CoinGeckoAPI:
    """Helper class to interact with CoinGecko API."""

    def __init__(self, hass):
        """Initialize the API helper."""
        self.hass = hass
        self._coin_list_cache = None

    async def get_coin_list(self) -> list[dict]:
        """Fetch the list of all available cryptocurrencies from CoinGecko."""
        if self._coin_list_cache:
            return self._coin_list_cache

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            url = f"{API_ENDPOINT}coins/list"
            async with session.get(url) as response:
                response.raise_for_status()
                self._coin_list_cache = await response.json()
                return self._coin_list_cache
        except Exception as err:
            _LOGGER.error(f"Error fetching coin list from CoinGecko: {err}")
            return []

    async def validate_cryptocurrency_ids(self, crypto_ids: list[str]) -> dict[str, bool]:
        """Validate if cryptocurrency IDs exist in CoinGecko.

        Returns a dict with crypto_id as key and boolean (valid/invalid) as value.
        """
        coin_list = await self.get_coin_list()
        if not coin_list:
            # If we can't fetch the list, assume all IDs are valid (fallback)
            return {crypto_id: True for crypto_id in crypto_ids}

        valid_ids = {coin["id"].lower() for coin in coin_list}
        return {
            crypto_id: crypto_id.lower() in valid_ids
            for crypto_id in crypto_ids
        }

    async def search_cryptocurrencies(self, query: str, limit: int = 10) -> list[dict]:
        """Search for cryptocurrencies by name or symbol.

        Returns a list of matching coins with id, name, and symbol.
        """
        coin_list = await self.get_coin_list()
        if not coin_list:
            return []

        query_lower = query.lower()
        matches = [
            coin for coin in coin_list
            if query_lower in coin["id"].lower()
            or query_lower in coin["name"].lower()
            or query_lower in coin["symbol"].lower()
        ]

        return matches[:limit]

    async def get_top_cryptocurrencies(self, limit: int = 10) -> list[dict]:
        """Fetch top cryptocurrencies by market cap from CoinGecko.

        Returns a list of top coins sorted by market cap rank.
        """
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            url = f"{API_ENDPOINT}coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                # Return simplified format matching coin_list
                return [
                    {
                        "id": coin["id"],
                        "name": coin["name"],
                        "symbol": coin["symbol"]
                    }
                    for coin in data
                ]
        except Exception as err:
            _LOGGER.error(f"Error fetching top cryptocurrencies from CoinGecko: {err}")
            # Fallback to hardcoded top 10
            return [
                {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"},
                {"id": "ethereum", "name": "Ethereum", "symbol": "eth"},
                {"id": "tether", "name": "Tether", "symbol": "usdt"},
                {"id": "binancecoin", "name": "BNB", "symbol": "bnb"},
                {"id": "solana", "name": "Solana", "symbol": "sol"},
                {"id": "ripple", "name": "XRP", "symbol": "xrp"},
                {"id": "usd-coin", "name": "USDC", "symbol": "usdc"},
                {"id": "cardano", "name": "Cardano", "symbol": "ada"},
                {"id": "dogecoin", "name": "Dogecoin", "symbol": "doge"},
                {"id": "tron", "name": "TRON", "symbol": "trx"},
            ]
