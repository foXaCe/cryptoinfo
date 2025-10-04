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

    def __init__(self, hass):
        """Initialize the API helper."""
        self.hass = hass

    async def get_user_stats(self, btc_address: str) -> dict | None:
        """Fetch user mining statistics from CKPool."""
        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            url = f"https://solo.ckpool.org/users/{btc_address}"

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
                data = await response.json()

                # CKPool returns JSON with hashrate data
                return self._parse_ckpool_data(data)
        except Exception as err:
            _LOGGER.error(f"Error fetching CKPool user stats for {btc_address}: {err}")
            return None

    def _parse_ckpool_data(self, data: dict) -> dict:
        """Parse CKPool JSON data to extract mining statistics."""

        # Convert hashrate string (e.g., "3.12T") to GH/s
        def convert_hashrate(hashrate_str: str) -> float:
            """Convert hashrate string to GH/s."""
            if not hashrate_str or hashrate_str == "0":
                return 0.0

            try:
                # Check if last char is a unit letter
                if hashrate_str[-1].isalpha():
                    value = float(hashrate_str[:-1])
                    unit = hashrate_str[-1]
                else:
                    # No unit, assume it's already in GH/s
                    value = float(hashrate_str)
                    unit = "G"

                # Convert to GH/s
                multipliers = {"K": 1e-6, "M": 1e-3, "G": 1, "T": 1e3, "P": 1e6}
                return value * multipliers.get(unit, 1)
            except (ValueError, IndexError):
                return 0.0

        return {
            "hashrate": convert_hashrate(data.get("hashrate1m", "0")),
            "hashrate_1h": convert_hashrate(data.get("hashrate1hr", "0")),
            "hashrate_24h": convert_hashrate(data.get("hashrate1d", "0")),
            "best_share": float(data.get("bestshare", 0)),
            "workers": int(data.get("workers", 0)),
            "blocks_found": 0,  # Not available in JSON
        }
