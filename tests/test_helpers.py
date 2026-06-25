"""Test the shared-data and storage helpers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.cryptoinfo.helper.crypto_info_data import CryptoInfoData
from custom_components.cryptoinfo.helper.storage_helper import (
    DEFAULT_MIN_TIME_BETWEEN_REQUESTS,
    CryptoInfoStore,
)


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
