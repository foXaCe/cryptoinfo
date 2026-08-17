"""Test the Cryptoinfo price sensor entities."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.api.coingecko_api import CoinGeckoAPI
from custom_components.cryptoinfo.const import (
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
)
from custom_components.cryptoinfo.coordinator import CryptoDataCoordinator
from custom_components.cryptoinfo.sensor import CryptoinfoDerivedSensor, CryptoinfoSensor

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
    """Only identity attributes remain; metrics are exposed as derived entities."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {"bitcoin": dict(MARKETS_RESPONSE[0])}
    sensor.coordinator.last_update_success = True
    attrs = sensor.extra_state_attributes
    assert attrs["cryptocurrency_id"] == "bitcoin"
    assert attrs["cryptocurrency_symbol"] == "btc"
    # Metrics are no longer attributes
    assert "baseprice" not in attrs
    assert "market_cap" not in attrs
    assert "rank" not in attrs


async def test_derived_sensor_native_value(hass: HomeAssistant) -> None:
    """Derived sensors read their metric from the API record via value_fn."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {"bitcoin": dict(MARKETS_RESPONSE[0])}
    sensor.coordinator.last_update_success = True

    from custom_components.cryptoinfo.sensor_descriptions import PRICE_DESCRIPTIONS

    for description in PRICE_DESCRIPTIONS:
        derived = CryptoinfoDerivedSensor(
            coordinator=sensor.coordinator,
            description=description,
            cryptocurrency_id="bitcoin",
            currency_name="usd",
            unit_of_measurement="$",
            base_unique_id="cryptoinfo_default_bitcoin_usd",
            id_name="",
        )
        value = derived.native_value
        # market_cap/rank/supplies are numeric; changes/ath too
        assert value is not None
        assert isinstance(value, float)


async def test_derived_sensor_unique_id_pattern(hass: HomeAssistant) -> None:
    """Derived unique ids extend the price base id with the metric key."""
    sensor = _make_sensor(hass)

    from custom_components.cryptoinfo.sensor_descriptions import PRICE_DESCRIPTIONS

    derived = CryptoinfoDerivedSensor(
        coordinator=sensor.coordinator,
        description=PRICE_DESCRIPTIONS[0],
        cryptocurrency_id="bitcoin",
        currency_name="usd",
        unit_of_measurement="$",
        base_unique_id="cryptoinfo_default_bitcoin_usd",
        id_name="",
    )
    assert derived.unique_id == "cryptoinfo_default_bitcoin_usd_market_cap"


async def test_derived_sensor_native_value_edge_cases(hass: HomeAssistant) -> None:
    """Derived sensors return None on missing/boolean/unparsable values."""
    sensor = _make_sensor(hass)
    sensor.coordinator.data = {"bitcoin": dict(MARKETS_RESPONSE[0])}
    sensor.coordinator.last_update_success = True

    from collections.abc import Callable

    from custom_components.cryptoinfo.sensor_descriptions import CryptoSensorEntityDescription

    def make_derived(value_fn: Callable[[dict[str, object]], object]) -> CryptoinfoDerivedSensor:
        return CryptoinfoDerivedSensor(
            coordinator=sensor.coordinator,
            description=CryptoSensorEntityDescription(
                key="edge", translation_key="crypto_market_cap", value_fn=value_fn
            ),
            cryptocurrency_id="bitcoin",
            currency_name="usd",
            unit_of_measurement="$",
            base_unique_id="cryptoinfo_default_bitcoin_usd",
            id_name="",
        )

    assert make_derived(lambda d: True).native_value is None  # bool
    assert make_derived(lambda d: None).native_value is None  # None
    assert make_derived(lambda d: "not-a-number").native_value is None  # unparsable -> ValueError
    assert make_derived(lambda d: {"key": None}["missing"]).native_value is None  # KeyError
    # coin absent from data
    sensor.coordinator.data = {"ethereum": {}}
    assert make_derived(lambda d: 42).native_value is None  # bitcoin missing


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
