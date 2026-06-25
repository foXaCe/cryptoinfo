"""Test the shared-data and storage helpers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
import pytest

from custom_components.cryptoinfo.helper.crypto_info_data import CryptoInfoData
from custom_components.cryptoinfo.helper.storage_helper import (
    DEFAULT_MIN_TIME_BETWEEN_REQUESTS,
    CryptoInfoStore,
)
from custom_components.cryptoinfo.helpers import build_price_unique_id


@pytest.mark.parametrize(
    ("id_name", "cryptocurrency_id", "currency_name", "expected"),
    [
        ("My Wallet", "bitcoin", "usd", "cryptoinfo_my_wallet_bitcoin_usd"),
        ("", "ethereum", "EUR", "cryptoinfo__ethereum_eur"),
        ("Trading Portfolio", "Bitcoin", "USD", "cryptoinfo_trading_portfolio_bitcoin_usd"),
    ],
)
def test_build_price_unique_id(id_name: str, cryptocurrency_id: str, currency_name: str, expected: str) -> None:
    """The price unique_id is lowercased, space-free and stable (no drift allowed)."""
    assert build_price_unique_id(id_name, cryptocurrency_id, currency_name) == expected


async def test_crypto_info_data_setter(hass: HomeAssistant) -> None:
    """The setter updates the value, the store and exposes a shared API client."""
    data = CryptoInfoData(hass)
    await data.async_initialize()
    assert data.min_time_between_requests == DEFAULT_MIN_TIME_BETWEEN_REQUESTS
    assert data.api is not None

    data.min_time_between_requests = 0.5
    assert data.min_time_between_requests == 0.5
    assert data.store.data["min_time_between_requests"] == 0.5
    await hass.async_block_till_done()


async def test_store_persists(hass: HomeAssistant) -> None:
    """Saved data is reloaded by a fresh store instance."""
    store = CryptoInfoStore(hass)
    await store.async_load()
    assert store.data["min_time_between_requests"] == DEFAULT_MIN_TIME_BETWEEN_REQUESTS

    store.data["min_time_between_requests"] = 2.0
    await store.async_save()

    store2 = CryptoInfoStore(hass)
    await store2.async_load()
    assert store2.data["min_time_between_requests"] == 2.0
