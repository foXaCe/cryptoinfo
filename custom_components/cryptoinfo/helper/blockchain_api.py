#!/usr/bin/env python3
"""
Blockchain API helper for Bitcoin network stats
Author: foXaCe
"""

from homeassistant.helpers import aiohttp_client
from ..const.const import _LOGGER

MEMPOOL_SPACE_API = "https://mempool.space/api"


class BlockchainAPI:
    """Helper class to interact with Mempool.space API for Bitcoin stats."""

    def __init__(self, hass):
        """Initialize the API helper."""
        self.hass = hass

    async def get_network_stats(self) -> dict | None:
        """Fetch Bitcoin network statistics from mempool.space."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)

            # Get mining stats (hashrate, difficulty)
            mining_url = f"{MEMPOOL_SPACE_API}/v1/mining/hashrate/3d"
            blocks_url = f"{MEMPOOL_SPACE_API}/blocks/tip/height"
            difficulty_url = f"{MEMPOOL_SPACE_API}/v1/difficulty-adjustment"

            async with session.get(mining_url) as mining_response:
                mining_response.raise_for_status()
                mining_data = await mining_response.json()

            async with session.get(blocks_url) as blocks_response:
                blocks_response.raise_for_status()
                block_height = await blocks_response.text()

            async with session.get(difficulty_url) as diff_response:
                diff_response.raise_for_status()
                difficulty_data = await diff_response.json()

            # Calculate halving info (every 210,000 blocks)
            current_height = int(block_height)
            next_halving = ((current_height // 210000) + 1) * 210000
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
            _LOGGER.error(f"Error fetching Bitcoin network stats: {err}")
            return None

    async def get_mempool_stats(self) -> dict | None:
        """Fetch Bitcoin mempool statistics from mempool.space."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)

            mempool_url = f"{MEMPOOL_SPACE_API}/mempool"
            fees_url = f"{MEMPOOL_SPACE_API}/v1/fees/recommended"

            async with session.get(mempool_url) as mempool_response:
                mempool_response.raise_for_status()
                mempool_data = await mempool_response.json()

            async with session.get(fees_url) as fees_response:
                fees_response.raise_for_status()
                fees_data = await fees_response.json()

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
            _LOGGER.error(f"Error fetching Bitcoin mempool stats: {err}")
            return None


class CKPoolAPI:
    """Helper class to interact with CKPool solo mining API."""

    def __init__(self, hass, pool_url: str = "solo.ckpool.org"):
        """Initialize the API helper."""
        self.hass = hass
        self.pool_url = pool_url

    async def get_user_stats(self, btc_address: str) -> dict | None:
        """Fetch user mining statistics from CKPool."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            url = f"https://{self.pool_url}/users/{btc_address}"

            async with session.get(url) as response:
                # 404 means address has no mining history - return empty stats
                if response.status == 404:
                    _LOGGER.debug(f"No mining history found for {btc_address} on CKPool")
                    return {
                        "hashrate": 0,
                        "hashrate_1h": 0,
                        "hashrate_24h": 0,
                        "best_share": 0,
                        "workers": 0,
                        "blocks_found": 0,
                    }

                response.raise_for_status()

                # Check content type
                content_type = response.headers.get('Content-Type', '')

                if 'application/json' in content_type:
                    # Global pool: direct JSON API
                    data = await response.json()
                    _LOGGER.debug(f"Got JSON data from {self.pool_url}: {data}")
                    result = self._parse_ckpool_data(data)
                    _LOGGER.debug(f"Parsed result: {result}")
                    return result
                elif 'text/html' in content_type:
                    # EU pool: Next.js app with embedded JSON
                    html = await response.text()
                    _LOGGER.debug(f"Got HTML response from {self.pool_url}, length: {len(html)}")
                    data = self._extract_json_from_html(html)
                    if data:
                        result = self._parse_ckpool_data(data)
                        _LOGGER.debug(f"Parsed result from HTML: {result}")
                        return result
                    else:
                        _LOGGER.error(f"Failed to extract JSON from HTML for {btc_address}")
                        return None
                else:
                    _LOGGER.error(f"Unexpected content type: {content_type}")
                    return None

        except Exception as err:
            _LOGGER.error(f"Error fetching CKPool user stats for {btc_address}: {err}")
            return None

    def _extract_json_from_html(self, html: str) -> dict | None:
        """Extract JSON data from Next.js HTML page."""
        import re
        import json

        # EU pool embeds JSON in the HTML within script tags, escaped as JavaScript strings
        # Pattern matches escaped JSON: \"hashrate1m\":\"1110000000000\"
        try:
            # Extract individual fields from escaped JSON strings
            hashrate1m = re.search(r'\\"hashrate1m\\":\\"(\d+)\\"', html)
            hashrate1hr = re.search(r'\\"hashrate1hr\\":\\"(\d+)\\"', html)
            hashrate1d = re.search(r'\\"hashrate1d\\":\\"(\d+)\\"', html)
            workers = re.search(r'\\"workers\\":\\"(\d+)\\"', html)
            bestshare = re.search(r'\\"bestshare\\":\\"(\d+\.?\d*)\\"', html)

            if hashrate1m:
                data = {
                    "hashrate1m": int(hashrate1m.group(1)),
                    "hashrate1hr": int(hashrate1hr.group(1)) if hashrate1hr else 0,
                    "hashrate1d": int(hashrate1d.group(1)) if hashrate1d else 0,
                    "workers": int(workers.group(1)) if workers else 0,
                    "bestshare": float(bestshare.group(1)) if bestshare else 0,
                }
                _LOGGER.debug(f"Extracted fields from escaped HTML: {data}")
                return data
        except (ValueError, AttributeError) as e:
            _LOGGER.debug(f"Field extraction error: {e}")
            pass

        _LOGGER.warning("Failed to extract any mining data from HTML")
        return None

    def _parse_ckpool_data(self, data: dict) -> dict:
        """Parse CKPool JSON data to extract mining statistics."""

        # Convert hashrate to GH/s (handles both string format and nanoseconds)
        def convert_hashrate(hashrate_value) -> float:
            """Convert hashrate to GH/s."""
            if not hashrate_value or hashrate_value == "0" or hashrate_value == 0:
                return 0.0

            try:
                # EU pool format: integer nanoseconds (e.g., 1060000000000)
                if isinstance(hashrate_value, (int, float)) and hashrate_value > 1000:
                    # Convert from H/s to GH/s
                    return round(hashrate_value / 1e9, 2)

                # Global pool format: string with unit (e.g., "3.12T")
                if isinstance(hashrate_value, str):
                    # Check if last char is a unit letter
                    if hashrate_value[-1].isalpha():
                        value = float(hashrate_value[:-1])
                        unit = hashrate_value[-1]
                        # Convert to GH/s
                        multipliers = {"K": 1e-6, "M": 1e-3, "G": 1, "T": 1e3, "P": 1e6}
                        return round(value * multipliers.get(unit, 1), 2)
                    else:
                        # Plain number as string
                        return round(float(hashrate_value), 2)

                return 0.0
            except (ValueError, IndexError, TypeError):
                return 0.0

        return {
            "hashrate": convert_hashrate(data.get("hashrate1m", 0)),
            "hashrate_1h": convert_hashrate(data.get("hashrate1hr", 0)),
            "hashrate_24h": convert_hashrate(data.get("hashrate1d", 0)),
            "best_share": float(data.get("bestshare", 0)),
            "workers": int(data.get("workers", 0)),
            "blocks_found": 0,  # Not available in JSON
        }
