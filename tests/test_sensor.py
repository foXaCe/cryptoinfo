"""Test the Cryptoinfo price sensor entities."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const.const import (
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
)
from custom_components.cryptoinfo.coordinator import CryptoDataCoordinator
from custom_components.cryptoinfo.helper.coingecko_api import CoinGeckoAPI
from custom_components.cryptoinfo.sensor import CryptoinfoSensor

from .conftest import MARKETS_RESPONSE, make_price_entry


def _make_sensor(hass: HomeAssistant, multiplier: str = "1") -> CryptoinfoSensor:
    api = CoinGeckoAPI(hass)
    coordinator = CryptoDataCoordinator(hass, api, "bitcoin", "usd", timedelta(minutes=5), "test")
    return CryptoinfoSensor(
        coordinator=coordinator,
        cryptocurrency_id="bitcoin",
        currency_name="usd",
        unit_of_measurement="$",
        multiplier=multiplier,
        id_name="test",
    )


async def test_native_value_and_multiplier(hass: HomeAssistant) -> None:
    """native_value multiplies the base price."""
    sensor = _make_sensor(hass, multiplier="2")
    sensor.coordinator.data = {"bitcoin": dict(MARKETS_RESPONSE[0])}
    sensor.coordinator.last_update_success = True
    assert sensor.native_value == 100000.0
    assert sensor.available is True
    assert sensor.translation_key == "crypto_price"
    assert sensor.unique_id == "cryptoinfo_test_bitcoin_usd"


async def test_unavailable_when_no_data(hass: HomeAssistant) -> None:
    """The sensor is unavailable and value None when data is missing."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {}
    sensor.coordinator.last_update_success = True
    assert sensor.available is False
    assert sensor.native_value is None
    # empty attributes still expose the keys
    attrs: dict[str, Any] = sensor.extra_state_attributes
    assert attrs["cryptocurrency_name"] is None


async def test_native_value_invalid_price(hass: HomeAssistant) -> None:
    """A non-numeric price returns None instead of raising."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {"bitcoin": {"current_price": "not-a-number"}}
    sensor.coordinator.last_update_success = True
    assert sensor.native_value is None


async def test_native_value_coin_absent(hass: HomeAssistant) -> None:
    """The sensor is unavailable when its coin is missing from the payload."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {"ethereum": {"current_price": 3000}}
    sensor.coordinator.last_update_success = True
    assert sensor.available is False
    assert sensor.native_value is None


async def test_extra_state_attributes(hass: HomeAssistant) -> None:
    """Attributes are mapped from the coordinator payload."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {"bitcoin": dict(MARKETS_RESPONSE[0])}
    sensor.coordinator.last_update_success = True
    attrs = sensor.extra_state_attributes
    assert attrs["baseprice"] == 50000.0
    assert attrs["market_cap"] == 950000000000
    assert attrs["rank"] == 1


async def test_options_override_update_frequency(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """Options take precedence over the original data for the update interval."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={CONF_UPDATE_FREQUENCY: 1})

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data.coordinator
    assert coordinator is not None
    assert coordinator.update_interval == timedelta(minutes=1)


async def test_multiplier_mismatch_creates_no_entity(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """A cryptos/multipliers length mismatch creates no entities."""
    entry = make_price_entry(cryptocurrency_ids="bitcoin,ethereum", multipliers="1")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_test_bitcoin_usd") is None
