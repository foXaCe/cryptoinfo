"""Test Cryptoinfo diagnostics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_price(
    hass: HomeAssistant,
    price_config_entry: MockConfigEntry,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """Diagnostics expose coordinator info for a price entry."""
    price_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(price_config_entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, price_config_entry)
    assert diag["entry"]["domain"] == "cryptoinfo"
    assert "main" in diag["runtime_data"]["coordinators"]
    assert diag["runtime_data"]["shared_data"]["min_time_between_requests"] is not None


async def test_diagnostics_redacts_btc_address(
    hass: HomeAssistant,
    ckpool_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """The Bitcoin address is redacted from diagnostics."""
    addr = ckpool_config_entry.data["btc_address"]
    aioclient_mock.get(
        f"https://solo.ckpool.org/users/{addr}",
        json={"hashrate1m": "1T", "workers": 1, "bestshare": 0, "bestever": "0"},
        headers={"Content-Type": "application/json"},
    )
    ckpool_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(ckpool_config_entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, ckpool_config_entry)
    assert diag["entry"]["data"]["btc_address"] == "**REDACTED**"
