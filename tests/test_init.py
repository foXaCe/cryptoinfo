"""Test Cryptoinfo integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo import async_migrate_entry
from custom_components.cryptoinfo.const.const import DOMAIN, CryptoInfoRuntimeData
from custom_components.cryptoinfo.exceptions import CryptoInfoConnectionError


async def test_setup_and_unload(
    hass: HomeAssistant,
    price_config_entry: MockConfigEntry,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """Full setup then unload of a price entry creates and removes the entity."""
    price_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(price_config_entry.entry_id)
    await hass.async_block_till_done()

    assert price_config_entry.state is ConfigEntryState.LOADED
    assert isinstance(price_config_entry.runtime_data, CryptoInfoRuntimeData)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_test_bitcoin_usd")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == 50000.0
    assert state.attributes["cryptocurrency_name"] == "Bitcoin"

    assert await hass.config_entries.async_unload(price_config_entry.entry_id)
    await hass.async_block_till_done()
    assert price_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_reload_entry(
    hass: HomeAssistant,
    price_config_entry: MockConfigEntry,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """Reloading an entry keeps it loaded."""
    price_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(price_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_reload(price_config_entry.entry_id)
    await hass.async_block_till_done()
    assert price_config_entry.state is ConfigEntryState.LOADED


async def test_migrate_entry_returns_true(
    hass: HomeAssistant,
    price_config_entry: MockConfigEntry,
) -> None:
    """The migration entrypoint is idempotent and returns True."""
    price_config_entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, price_config_entry) is True


async def test_setup_retry_when_init_fails(
    hass: HomeAssistant,
    price_config_entry: MockConfigEntry,
) -> None:
    """A failed shared-data init raises ConfigEntryNotReady (SETUP_RETRY)."""
    price_config_entry.add_to_hass(hass)
    with patch("custom_components.cryptoinfo.CryptoInfoData") as mock_data_cls:
        instance = mock_data_cls.return_value
        instance.async_initialize = AsyncMock(side_effect=CryptoInfoConnectionError("boom"))
        assert not await hass.config_entries.async_setup(price_config_entry.entry_id)
        await hass.async_block_till_done()
    assert price_config_entry.state is ConfigEntryState.SETUP_RETRY
