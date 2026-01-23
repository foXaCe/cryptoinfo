"""Fixtures for Cryptoinfo tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

from custom_components.cryptoinfo.const.const import DOMAIN


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        f"custom_components.{DOMAIN}.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_coingecko_api() -> Generator[AsyncMock, None, None]:
    """Mock CoinGecko API responses."""
    with patch(f"custom_components.{DOMAIN}.helper.coingecko_api.CoinGeckoAPI") as mock_api:
        mock_instance = AsyncMock()
        mock_instance.get_price = AsyncMock(
            return_value={
                "bitcoin": {
                    "usd": 50000.0,
                    "usd_24h_change": 2.5,
                    "usd_24h_vol": 30000000000,
                    "usd_market_cap": 950000000000,
                }
            }
        )
        mock_instance.get_coin_data = AsyncMock(
            return_value={
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "market_data": {
                    "current_price": {"usd": 50000.0},
                    "price_change_percentage_24h": 2.5,
                },
            }
        )
        mock_api.return_value = mock_instance
        yield mock_instance


@pytest.fixture
async def hass_setup(hass: HomeAssistant) -> HomeAssistant:
    """Set up Home Assistant for testing."""
    await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()
    return hass
