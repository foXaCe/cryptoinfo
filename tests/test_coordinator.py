"""Test the Cryptoinfo price coordinator."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const.const import API_ENDPOINT
from custom_components.cryptoinfo.coordinator import CryptoDataCoordinator
from custom_components.cryptoinfo.helper.coingecko_api import CoinGeckoAPI


async def test_update_success(hass: HomeAssistant, mock_coingecko: AiohttpClientMocker) -> None:
    """A successful fetch is keyed by coin id."""
    api = CoinGeckoAPI(hass)
    coordinator = CryptoDataCoordinator(hass, api, "bitcoin", "usd", timedelta(minutes=5), "test")
    data = await coordinator._async_update_data()
    assert "bitcoin" in data
    assert data["bitcoin"]["current_price"] == 50000.0


async def test_update_rate_limited(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A 429 surfaces as UpdateFailed."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", status=429, headers={"Retry-After": "0"})
    api = CoinGeckoAPI(hass)
    coordinator = CryptoDataCoordinator(hass, api, "bitcoin", "usd", timedelta(minutes=5), "test")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_update_server_error(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A 500 surfaces as UpdateFailed."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", status=500)
    api = CoinGeckoAPI(hass)
    coordinator = CryptoDataCoordinator(hass, api, "bitcoin", "usd", timedelta(minutes=5), "test")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
