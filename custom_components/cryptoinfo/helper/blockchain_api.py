"""Blockchain API helper for Bitcoin network stats.

Author: foXaCe
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import re
from typing import TYPE_CHECKING, Any, cast

import aiohttp
from homeassistant.helpers import aiohttp_client

from ..const.const import _LOGGER
from ..exceptions import (
    CryptoInfoConnectionError,
    CryptoInfoInvalidResponseError,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

MEMPOOL_SPACE_API = "https://mempool.space/api"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes
BITCOIN_HALVING_INTERVAL = 210_000  # blocks between halvings


class BlockchainAPI:
    """Helper class to interact with Mempool.space API for Bitcoin stats."""

    __slots__ = ("_circuit_open_until", "_consecutive_failures", "hass")

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API helper."""
        self.hass = hass
        self._consecutive_failures = 0
        self._circuit_open_until: datetime | None = None

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
                "Circuit breaker opened after %d failures",
                self._consecutive_failures,
            )

    # =========================================================================
    # REQUEST HANDLING WITH RETRY
    # =========================================================================

    async def _request(self, url: str, *, retry: bool = True, parse_json: bool = True) -> Any:
        """Make API request with retry and circuit breaker."""
        self._check_circuit_breaker()

        last_exception: Exception | None = None
        retries = MAX_RETRIES if retry else 1

        for attempt in range(retries):
            try:
                session = aiohttp_client.async_get_clientsession(self.hass)

                async with asyncio.timeout(DEFAULT_TIMEOUT):
                    async with session.get(url) as response:
                        if response.status >= 400:
                            raise CryptoInfoConnectionError(f"HTTP error: {response.status}", response.status)

                        self._record_success()

                        if parse_json:
                            return await response.json()
                        return await response.text()

            except aiohttp.ClientError as err:
                last_exception = CryptoInfoConnectionError(f"Connection error: {err}")
                _LOGGER.debug("Request failed (attempt %d/%d): %s", attempt + 1, retries, err)

            except TimeoutError:
                last_exception = CryptoInfoConnectionError("Request timeout")
                _LOGGER.debug("Request timeout (attempt %d/%d)", attempt + 1, retries)

            if attempt < retries - 1:
                delay = RETRY_DELAY * (2**attempt)  # Exponential backoff
                await asyncio.sleep(delay)

        self._record_failure()
        raise last_exception or CryptoInfoConnectionError("Request failed")

    # =========================================================================
    # API METHODS
    # =========================================================================

    async def get_network_stats(self) -> dict | None:
        """Fetch Bitcoin network statistics from mempool.space using parallel requests."""
        try:
            # Parallel requests for better performance
            mining_task = self._request(f"{MEMPOOL_SPACE_API}/v1/mining/hashrate/3d")
            blocks_task = self._request(f"{MEMPOOL_SPACE_API}/blocks/tip/height", parse_json=False)
            difficulty_task = self._request(f"{MEMPOOL_SPACE_API}/v1/difficulty-adjustment")

            results = await asyncio.gather(
                mining_task,
                blocks_task,
                difficulty_task,
                return_exceptions=True,
            )

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    _LOGGER.error("Error in parallel request %d: %s", i, result)
                    return None

            # Type narrowing after exception check
            mining_data = cast(dict[str, Any], results[0])
            block_height_str = cast(str, results[1])
            difficulty_data = cast(dict[str, Any], results[2])

            # Calculate halving info
            current_height = int(block_height_str)
            next_halving = ((current_height // BITCOIN_HALVING_INTERVAL) + 1) * BITCOIN_HALVING_INTERVAL
            blocks_until_halving = next_halving - current_height

            return {
                "hashrate": mining_data.get("currentHashrate", 0) / 1e18,  # Convert to EH/s
                "difficulty": difficulty_data.get("difficulty", 0),
                "block_height": current_height,
                "next_difficulty_block": difficulty_data.get("nextRetargetHeight", 0),
                "blocks_until_retarget": difficulty_data.get("remainingBlocks", 0),
                "difficulty_change": difficulty_data.get("difficultyChange", 0),
                "next_halving_block": next_halving,
                "blocks_until_halving": blocks_until_halving,
            }
        except Exception as err:
            _LOGGER.error("Error fetching Bitcoin network stats: %s", err)
            return None

    async def get_mempool_stats(self) -> dict | None:
        """Fetch Bitcoin mempool statistics from mempool.space using parallel requests."""
        try:
            # Parallel requests for better performance
            mempool_task = self._request(f"{MEMPOOL_SPACE_API}/mempool")
            fees_task = self._request(f"{MEMPOOL_SPACE_API}/v1/fees/recommended")

            results = await asyncio.gather(
                mempool_task,
                fees_task,
                return_exceptions=True,
            )

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    _LOGGER.error("Error in parallel request %d: %s", i, result)
                    return None

            # Type narrowing after exception check
            mempool_data = cast(dict[str, Any], results[0])
            fees_data = cast(dict[str, Any], results[1])

            return {
                "mempool_size": mempool_data.get("count", 0),
                "mempool_bytes": mempool_data.get("vsize", 0) / 1_000_000,  # Convert to MB
                "fee_fastest": fees_data.get("fastestFee", 0),
                "fee_half_hour": fees_data.get("halfHourFee", 0),
                "fee_hour": fees_data.get("hourFee", 0),
                "fee_economy": fees_data.get("economyFee", 0),
                "fee_minimum": fees_data.get("minimumFee", 0),
            }
        except Exception as err:
            _LOGGER.error("Error fetching Bitcoin mempool stats: %s", err)
            return None


class CKPoolAPI:
    """Helper class to interact with CKPool solo mining API."""

    __slots__ = ("_circuit_open_until", "_consecutive_failures", "hass", "pool_url")

    def __init__(self, hass: HomeAssistant, pool_url: str = "solo.ckpool.org") -> None:
        """Initialize the API helper."""
        self.hass = hass
        self.pool_url = pool_url
        self._consecutive_failures = 0
        self._circuit_open_until: datetime | None = None

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
                "Circuit breaker opened after %d failures",
                self._consecutive_failures,
            )

    async def get_user_stats(self, btc_address: str) -> dict | None:
        """Fetch user mining statistics from CKPool with retry."""
        self._check_circuit_breaker()

        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                session = aiohttp_client.async_get_clientsession(self.hass)
                url = f"https://{self.pool_url}/users/{btc_address}"

                async with asyncio.timeout(DEFAULT_TIMEOUT):
                    async with session.get(url) as response:
                        # 404 means address has no mining history - return empty stats
                        if response.status == 404:
                            _LOGGER.debug("No mining history found for %s on CKPool", btc_address)
                            self._record_success()
                            return {
                                "hashrate": 0,
                                "hashrate_1h": 0,
                                "hashrate_24h": 0,
                                "best_share": 0,
                                "best_ever": 0,
                                "workers": 0,
                                "blocks_found": 0,
                            }

                        if response.status >= 400:
                            raise CryptoInfoConnectionError(f"HTTP error: {response.status}", response.status)

                        # Check content type
                        content_type = response.headers.get("Content-Type", "")

                        if "application/json" in content_type:
                            # Global pool: direct JSON API
                            data = await response.json()
                            _LOGGER.debug("Got JSON data from %s: %s", self.pool_url, data)
                            self._record_success()
                            return self._parse_ckpool_data(data)

                        if "text/html" in content_type:
                            # EU pool: Next.js app with embedded JSON
                            html = await response.text()
                            _LOGGER.debug("Got HTML response from %s, length: %d", self.pool_url, len(html))
                            data = self._extract_json_from_html(html)
                            if data:
                                self._record_success()
                                return self._parse_ckpool_data(data)
                            raise CryptoInfoInvalidResponseError(f"Failed to extract JSON from HTML for {btc_address}")

                        raise CryptoInfoInvalidResponseError(f"Unexpected content type: {content_type}")

            except CryptoInfoInvalidResponseError as err:
                # Invalid response: record failure and don't retry
                _LOGGER.debug("Invalid response: %s", err)
                self._record_failure()
                return None

            except aiohttp.ClientError as err:
                last_exception = CryptoInfoConnectionError(f"Connection error: {err}")
                _LOGGER.debug("Request failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, err)

            except TimeoutError:
                last_exception = CryptoInfoConnectionError("Request timeout")
                _LOGGER.debug("Request timeout (attempt %d/%d)", attempt + 1, MAX_RETRIES)

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2**attempt)
                await asyncio.sleep(delay)

        self._record_failure()
        _LOGGER.error("Error fetching CKPool user stats for %s: %s", btc_address, last_exception)
        return None

    def _extract_json_from_html(self, html: str) -> dict | None:
        """Extract JSON data from Next.js HTML page."""
        # EU pool embeds JSON in the HTML within script tags, escaped as JavaScript strings
        try:
            # Extract hashrate fields (always strings in quotes)
            hashrate1m = re.search(r'\\"hashrate1m\\":\\"(\d+)\\"', html)
            hashrate1hr = re.search(r'\\"hashrate1hr\\":\\"(\d+)\\"', html)
            hashrate1d = re.search(r'\\"hashrate1d\\":\\"(\d+)\\"', html)

            # Count workers in the workers array
            workers_match = re.search(r'\\"workers\\":\[([^\]]+)\]', html)
            workers_count = 0
            if workers_match:
                # Count objects by counting "id" fields
                worker_ids = re.findall(r'\\"id\\"', workers_match.group(1))
                workers_count = len(worker_ids)

            # Extract bestShare (JavaScript number, not quoted) and bestEver (quoted string)
            best_share = re.search(r'\\"bestShare\\":(\d+\.?\d*)', html)
            best_ever = re.search(r'\\"bestEver\\":\\"(\d+)', html)

            if hashrate1m:
                data = {
                    "hashrate1m": int(hashrate1m.group(1)),
                    "hashrate1hr": int(hashrate1hr.group(1)) if hashrate1hr else 0,
                    "hashrate1d": int(hashrate1d.group(1)) if hashrate1d else 0,
                    "workers": workers_count,
                    "bestshare": float(best_share.group(1)) if best_share else 0,
                    "bestever": float(best_ever.group(1)) if best_ever else 0,
                }
                _LOGGER.debug("Extracted fields from escaped HTML: %s", data)
                return data
        except (ValueError, AttributeError) as e:
            _LOGGER.debug("Field extraction error: %s", e)

        _LOGGER.warning("Failed to extract any mining data from HTML")
        return None

    def _parse_ckpool_data(self, data: dict) -> dict:
        """Parse CKPool JSON data to extract mining statistics."""

        def convert_hashrate(hashrate_value: str | int | float | None) -> float:
            """Convert hashrate to GH/s.

            Handles two formats:
            - EU pool: integer in H/s (e.g., 1060000000000 = ~1 TH/s)
            - Global pool: string with unit suffix (e.g., "3.12T" = 3.12 TH/s)
            """
            if not hashrate_value or hashrate_value == "0" or hashrate_value == 0:
                return 0.0

            try:
                # Global pool format: string with unit (e.g., "3.12T")
                if isinstance(hashrate_value, str):
                    # Check if last char is a unit letter
                    if hashrate_value[-1].isalpha():
                        value = float(hashrate_value[:-1])
                        unit = hashrate_value[-1]
                        # Convert to GH/s
                        multipliers = {"K": 1e-6, "M": 1e-3, "G": 1, "T": 1e3, "P": 1e6}
                        return round(value * multipliers.get(unit, 1), 2)
                    # Plain number as string - treat as H/s
                    return round(float(hashrate_value) / 1e9, 2)

                # EU pool format: integer in H/s (e.g., 1060000000000)
                # Any numeric value is treated as H/s and converted to GH/s
                if isinstance(hashrate_value, int):
                    return round(hashrate_value / 1e9, 2)

                return 0.0
            except (ValueError, IndexError, TypeError):
                return 0.0

        return {
            "hashrate": convert_hashrate(data.get("hashrate1m", 0)),
            "hashrate_1h": convert_hashrate(data.get("hashrate1hr", 0)),
            "hashrate_24h": convert_hashrate(data.get("hashrate1d", 0)),
            "best_share": float(data.get("bestshare", 0)),
            "best_ever": float(data.get("bestever", 0)),
            "workers": int(data.get("workers", 0)),
            "blocks_found": 0,  # Not available in JSON
        }
