"""Test Cryptoinfo mining sensors."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const.const import DOMAIN
from custom_components.cryptoinfo.mining_sensor import CKPoolMiningSensor


async def test_btc_network_sensor(
    hass: HomeAssistant,
    network_config_entry: MockConfigEntry,
    mock_mempool: AiohttpClientMocker,
) -> None:
    """Bitcoin Network sensor exposes hashrate (EH/s) and network attributes."""
    network_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(network_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_btc_network_")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 600.0  # 6e20 H/s -> 600 EH/s
    assert state.attributes["block_height"] == 870000
    assert state.attributes["blocks_until_halving"] == 210000 * 5 - 870000


async def test_btc_mempool_sensor(
    hass: HomeAssistant,
    mempool_config_entry: MockConfigEntry,
    mock_mempool: AiohttpClientMocker,
) -> None:
    """Bitcoin Mempool sensor exposes tx count and fee attributes."""
    mempool_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mempool_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_btc_mempool_")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert int(state.state) == 12000
    assert state.attributes["fee_fastest"] == "20 sat/vB"
    assert state.attributes["mempool_mb"] == 5.0


async def test_ckpool_sensor_global_json(
    hass: HomeAssistant,
    ckpool_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """CKPool sensor parses the Global pool JSON API."""
    addr = ckpool_config_entry.data["btc_address"]
    aioclient_mock.get(
        f"https://solo.ckpool.org/users/{addr}",
        json={
            "hashrate1m": "3.12T",
            "hashrate1hr": "3.00T",
            "hashrate1d": "2.50T",
            "bestshare": 1234567.0,
            "bestever": "9876543",
            "workers": 2,
        },
        headers={"Content-Type": "application/json"},
    )

    ckpool_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(ckpool_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_ckpool_bc1qexam")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 3120.0  # 3.12T -> 3120 GH/s
    assert state.attributes["workers"] == 2


async def test_ckpool_missing_address_fails_setup(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A CKPool entry without a BTC address does not create an entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="CKPool Mining",
        data={"sensor_type": "ckpool_mining", "id": "", "update_frequency": 5},
        unique_id="ckpool_noaddr",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Setup returns True (platform forwarded) but no entity is created.
    assert entry.state is ConfigEntryState.LOADED
    assert not hass.states.async_entity_ids("sensor")


def test_ckpool_format_share() -> None:
    """The share formatter uses G/M suffixes."""
    assert CKPoolMiningSensor._format_share(2.5e9) == "2.50 G"
    assert CKPoolMiningSensor._format_share(3.0e6) == "3.00 M"
    assert CKPoolMiningSensor._format_share(500) == "500"


async def test_mining_sensors_unavailable_without_data(hass: HomeAssistant) -> None:
    """Mining sensors report unavailable and None values without data."""
    from datetime import timedelta

    from custom_components.cryptoinfo.mining_sensor import (
        BTCMempoolCoordinator,
        BTCMempoolSensor,
        BTCNetworkCoordinator,
        BTCNetworkSensor,
        CKPoolCoordinator,
        CKPoolMiningSensor,
    )

    net = BTCNetworkSensor(BTCNetworkCoordinator(hass, timedelta(minutes=5)), "x")
    mem = BTCMempoolSensor(BTCMempoolCoordinator(hass, timedelta(minutes=5)), "x")
    ck = CKPoolMiningSensor(CKPoolCoordinator(hass, "addr", "solo.ckpool.org", timedelta(minutes=5)), "x", "addr")

    for sensor in (net, mem, ck):
        sensor.coordinator.data = None
        assert sensor.available is False
        assert sensor.native_value is None
        assert sensor.extra_state_attributes == {}


async def test_mining_coordinator_timeouts(hass: HomeAssistant) -> None:
    """A timeout in any mining coordinator surfaces as UpdateFailed."""
    from datetime import timedelta
    from unittest.mock import patch

    from homeassistant.helpers.update_coordinator import UpdateFailed
    import pytest

    from custom_components.cryptoinfo.helper.blockchain_api import BlockchainAPI, CKPoolAPI
    from custom_components.cryptoinfo.mining_sensor import (
        BTCMempoolCoordinator,
        BTCNetworkCoordinator,
        CKPoolCoordinator,
    )

    network = BTCNetworkCoordinator(hass, timedelta(minutes=5))
    mempool = BTCMempoolCoordinator(hass, timedelta(minutes=5))
    ckpool = CKPoolCoordinator(hass, "addr", "solo.ckpool.org", timedelta(minutes=5))

    with patch.object(BlockchainAPI, "get_network_stats", side_effect=TimeoutError), pytest.raises(UpdateFailed):
        await network._async_update_data()
    with patch.object(BlockchainAPI, "get_mempool_stats", side_effect=TimeoutError), pytest.raises(UpdateFailed):
        await mempool._async_update_data()
    with patch.object(CKPoolAPI, "get_user_stats", side_effect=TimeoutError), pytest.raises(UpdateFailed):
        await ckpool._async_update_data()
