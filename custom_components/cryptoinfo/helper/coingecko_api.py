"""CoinGecko API helper for Cryptoinfo.

Author: Johnny Visser
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.helpers import aiohttp_client

from ..const.const import _LOGGER, API_ENDPOINT
from ..exceptions import (
    CryptoInfoConnectionError,
    CryptoInfoInvalidResponseError,
    CryptoInfoRateLimitError,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
RATE_LIMIT_CALLS = 10  # CoinGecko free tier: 10-30 calls/min
RATE_LIMIT_PERIOD = 60  # seconds
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes


class CoinGeckoAPI:
    """Helper class to interact with CoinGecko API with resilience patterns."""

    __slots__ = (
        "_circuit_open_until",
        "_coin_list_cache",
        "_consecutive_failures",
        "_request_timestamps",
        "hass",
    )

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API helper."""
        self.hass = hass
        self._coin_list_cache: list[dict] | None = None
        # Rate limiting
        self._request_timestamps: list[datetime] = []
        # Circuit breaker
        self._consecutive_failures = 0
        self._circuit_open_until: datetime | None = None

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        now = datetime.now(UTC)

        # Clean old timestamps
        cutoff = now - timedelta(seconds=RATE_LIMIT_PERIOD)
        self._request_timestamps = [ts for ts in self._request_timestamps if ts > cutoff]

        # Check if rate limited
        if len(self._request_timestamps) >= RATE_LIMIT_CALLS:
            oldest = self._request_timestamps[0]
            wait_time = (oldest + timedelta(seconds=RATE_LIMIT_PERIOD) - now).total_seconds()
            if wait_time > 0:
                _LOGGER.warning("Rate limited, waiting %.1f seconds", wait_time)
                await asyncio.sleep(wait_time)

        self._request_timestamps.append(now)

    # =========================================================================
    # CIRCUIT BREAKER
    # =========================================================================

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker is open."""
        if self._circuit_open_until and datetime.now(UTC) < self._circuit_open_until:
            raise CryptoInfoConnectionError(f"Circuit breaker open until {self._circuit_open_until}")

    def _record_success(self) -> None:
        """Record successful request."""
        self._consecutive_failures = 0
        self._circuit_open_until = None

    def _record_failure(self) -> None:
        """Record failed request and potentially open circuit."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = datetime.now(UTC) + timedelta(seconds=CIRCUIT_BREAKER_TIMEOUT)
            _LOGGER.warning(
                "Circuit breaker opened after %d failures, will retry at %s",
                self._consecutive_failures,
                self._circuit_open_until,
            )

    # =========================================================================
    # REQUEST HANDLING WITH RETRY
    # =========================================================================

    async def _request(
        self,
        url: str,
        *,
        retry: bool = True,
    ) -> Any:
        """Make API request with retry, rate limiting, and circuit breaker."""
        self._check_circuit_breaker()
        await self._check_rate_limit()

        last_exception: Exception | None = None
        retries = MAX_RETRIES if retry else 1

        for attempt in range(retries):
            try:
                session = aiohttp_client.async_get_clientsession(self.hass)

                async with asyncio.timeout(DEFAULT_TIMEOUT):
                    async with session.get(url) as response:
                        return await self._handle_response(response)

            except CryptoInfoRateLimitError as err:
                # Rate limit: wait for retry_after and retry
                _LOGGER.warning(
                    "Rate limited by API, waiting %d seconds (attempt %d/%d)",
                    err.retry_after,
                    attempt + 1,
                    retries,
                )
                last_exception = err
                if attempt < retries - 1:
                    await asyncio.sleep(err.retry_after)
                    continue

            except CryptoInfoInvalidResponseError as err:
                # Invalid response: record failure and don't retry
                _LOGGER.debug("Invalid response: %s", err)
                self._record_failure()
                raise

            except aiohttp.ClientError as err:
                last_exception = CryptoInfoConnectionError(f"Connection error: {err}")
                _LOGGER.debug(
                    "Request failed (attempt %d/%d): %s",
                    attempt + 1,
                    retries,
                    err,
                )

            except TimeoutError:
                last_exception = CryptoInfoConnectionError("Request timeout")
                _LOGGER.debug(
                    "Request timeout (attempt %d/%d)",
                    attempt + 1,
                    retries,
                )

            if attempt < retries - 1:
                delay = RETRY_DELAY * (2**attempt)  # Exponential backoff
                await asyncio.sleep(delay)

        self._record_failure()
        raise last_exception or CryptoInfoConnectionError("Request failed")

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """Handle API response."""
        if response.status == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise CryptoInfoRateLimitError("Rate limit exceeded", retry_after=retry_after)

        if response.status >= 500:
            raise CryptoInfoConnectionError(f"Server error: {response.status}", response.status)

        if response.status >= 400:
            raise CryptoInfoConnectionError(f"Client error: {response.status}", response.status)

        try:
            data = await response.json()
            self._record_success()
            return data
        except Exception as err:
            raise CryptoInfoInvalidResponseError(f"Invalid JSON response: {err}") from err

    # =========================================================================
    # API METHODS
    # =========================================================================

    async def get_coin_list(self) -> list[dict]:
        """Fetch the list of all available cryptocurrencies from CoinGecko."""
        if self._coin_list_cache:
            return self._coin_list_cache

        try:
            url = f"{API_ENDPOINT}coins/list"
            self._coin_list_cache = await self._request(url)
            return self._coin_list_cache or []
        except Exception as err:
            _LOGGER.error("Error fetching coin list from CoinGecko: %s", err)
            return []

    async def validate_cryptocurrency_ids(self, crypto_ids: list[str]) -> dict[str, bool]:
        """Validate if cryptocurrency IDs exist in CoinGecko.

        Returns a dict with crypto_id as key and boolean (valid/invalid) as value.
        """
        coin_list = await self.get_coin_list()
        if not coin_list:
            # If we can't fetch the list, assume all IDs are valid (fallback)
            return dict.fromkeys(crypto_ids, True)

        valid_ids = {coin["id"].lower() for coin in coin_list}
        return {crypto_id: crypto_id.lower() in valid_ids for crypto_id in crypto_ids}

    async def search_cryptocurrencies(self, query: str, limit: int = 10) -> list[dict]:
        """Search for cryptocurrencies by name or symbol.

        Returns a list of matching coins with id, name, and symbol.
        """
        coin_list = await self.get_coin_list()
        if not coin_list:
            return []

        query_lower = query.lower()
        matches = [
            coin
            for coin in coin_list
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
            url = f"{API_ENDPOINT}coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
            data = await self._request(url)
            # Return simplified format matching coin_list
            return [{"id": coin["id"], "name": coin["name"], "symbol": coin["symbol"]} for coin in data]
        except Exception as err:
            _LOGGER.error("Error fetching top cryptocurrencies from CoinGecko: %s", err)
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
