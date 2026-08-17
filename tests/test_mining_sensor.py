"""Test Cryptoinfo mining sensors."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const import DOMAIN
from custom_components.cryptoinfo.mining_sensor import CKPoolMiningSensor

from .conftest import wait_for_state


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
    state = await wait_for_state(hass, entity_id)
    assert float(state.state) == 600.0  # 6e20 H/s -> 600 EH/s

    # Metrics are now dedicated derived entities
    block_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_btc_network__block_height")
    assert block_entity is not None
    block_state = await wait_for_state(hass, block_entity)
    assert float(block_state.state) == 870000
    halving_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_btc_network__blocks_until_halving")
    assert halving_entity is not None
    halving_state = await wait_for_state(hass, halving_entity)
    assert float(halving_state.state) == 210000 * 5 - 870000


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
    state = await wait_for_state(hass, entity_id)
    assert int(state.state) == 12000

    # Metrics are now dedicated derived entities
    fee_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_btc_mempool__fee_fastest")
    assert fee_entity is not None
    fee_state = await wait_for_state(hass, fee_entity)
    assert float(fee_state.state) == 20.0
    assert fee_state.attributes["unit_of_measurement"] == "sat/vB"
    mempool_mb_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_btc_mempool__mempool_mb")
    assert mempool_mb_entity is not None
    mempool_mb_state = await wait_for_state(hass, mempool_mb_entity)
    assert float(mempool_mb_state.state) == 5.0


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
    state = await wait_for_state(hass, entity_id)
    assert float(state.state) == 3120.0  # 3.12T -> 3120 GH/s

    # Workers is now a dedicated derived entity
    workers_entity = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_ckpool_bc1qexam_workers")
    assert workers_entity is not None
    workers_state = await wait_for_state(hass, workers_entity)
    assert float(workers_state.state) == 2


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


async def test_mining_sensors_unavailable_without_data(hass: HomeAssistant) -> None:
    """Mining sensors report unavailable and None values without data."""
    from datetime import timedelta

    from custom_components.cryptoinfo.mining_sensor import (
        BTCMempoolCoordinator,
        BTCMempoolSensor,
        BTCNetworkCoordinator,
        BTCNetworkSensor,
        CKPoolCoordinator,
    )

    net = BTCNetworkSensor(BTCNetworkCoordinator(hass, timedelta(minutes=5)), "x")
    mem = BTCMempoolSensor(BTCMempoolCoordinator(hass, timedelta(minutes=5)), "x")
    ck = CKPoolMiningSensor(CKPoolCoordinator(hass, "addr", "solo.ckpool.org", timedelta(minutes=5)), "x", "addr")

    for sensor in (net, mem, ck):
        sensor.coordinator.data = None
        assert sensor.available is False
        assert sensor.native_value is None
        if sensor is ck:
            assert sensor.extra_state_attributes == {"btc_address": "addr"}


async def test_mining_coordinator_timeouts(hass: HomeAssistant) -> None:
    """A timeout in any mining coordinator surfaces as UpdateFailed."""
    from datetime import timedelta
    from unittest.mock import patch

    from homeassistant.helpers.update_coordinator import UpdateFailed
    import pytest

    from custom_components.cryptoinfo.api.blockchain_api import BlockchainAPI, CKPoolAPI
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
