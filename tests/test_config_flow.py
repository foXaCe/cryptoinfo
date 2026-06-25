"""Test the Cryptoinfo config, reconfigure, reauth and options flows."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const.const import API_ENDPOINT, DOMAIN

from .conftest import make_price_entry


@pytest.fixture
def bypass_setup() -> Generator[None]:
    """Avoid real entry setup while exercising the flow logic."""
    with patch("custom_components.cryptoinfo.async_setup_entry", return_value=True):
        yield


async def test_user_price_flow(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """The full price flow creates an entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "price"})
    assert result["step_id"] == "price_search"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    assert result["step_id"] == "select_crypto"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    assert result["step_id"] == "configure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "wallet",
            "multipliers": "1",
            "currency_name": "usd",
            "unit_of_measurement": "$",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["cryptocurrency_ids"] == "bitcoin"


async def test_user_price_default_browse(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """An empty search browses the top cryptocurrencies."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "price"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": ""})
    assert result["step_id"] == "select_crypto"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"multipliers": "1", "currency_name": "usd", "update_frequency": 5, "min_time_between_requests": 0},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Empty id falls back to a cryptos+currency unique id.
    assert result["result"].unique_id == "bitcoin_usd"


async def test_reconfigure_entry_not_found(hass: HomeAssistant) -> None:
    """Reconfigure aborts when the entry is gone."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": "does_not_exist"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"


async def test_reconfigure_price_deselect_removes_crypto(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Deselecting a crypto during reconfigure drops it from the entry."""
    entry = make_price_entry(cryptocurrency_ids="bitcoin, ethereum", multipliers="1, 1")
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    # Empty search -> default browse merges top + existing, all pre-selected.
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": ""})
    assert result["step_id"] == "reconfigure_select"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "test",
            "multipliers": "1",
            "currency_name": "usd",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["cryptocurrency_ids"] == "bitcoin"


async def test_user_price_no_crypto_selected(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Selecting no cryptocurrency raises an error."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "price"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": []})
    assert result["step_id"] == "select_crypto"
    assert result["errors"] == {"base": "no_crypto_selected"}


async def test_user_price_no_results(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """A search with no match returns to the search step."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "price"})
    # An empty search bounces straight back to the search step (no matches).
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "zzzznomatch"})
    assert result["step_id"] == "price_search"


async def test_user_price_multiplier_mismatch(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """A multipliers/cryptos count mismatch raises an error."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "price"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"multipliers": "1,2", "currency_name": "usd", "update_frequency": 5, "min_time_between_requests": 0},
    )
    assert result["step_id"] == "configure"
    assert result["errors"]["base"] == "mismatch_values"


async def test_user_price_already_configured(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """A duplicate identifier aborts the flow."""
    make_price_entry(id="wallet").add_to_hass(hass)
    # Override unique_id to match what the flow will compute.
    existing = MockConfigEntry(domain=DOMAIN, data={"id": "wallet"}, unique_id="wallet")
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "price"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "wallet",
            "multipliers": "1",
            "currency_name": "usd",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_btc_network_flow(hass: HomeAssistant, bypass_setup: None) -> None:
    """The Bitcoin network flow creates an entry without an address."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "btc_network"})
    assert result["step_id"] == "mining_config"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"id": "net", "update_frequency": 5})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["sensor_type"] == "btc_network"


async def test_user_ckpool_flow(hass: HomeAssistant, bypass_setup: None) -> None:
    """The CKPool flow creates an entry with an address."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "ckpool_mining"})
    assert result["step_id"] == "mining_config"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"id": "miner", "btc_address": "bc1qexample", "ckpool_region": "solo.ckpool.org", "update_frequency": 5},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["btc_address"] == "bc1qexample"


async def test_user_ckpool_requires_address(hass: HomeAssistant, bypass_setup: None) -> None:
    """CKPool without a Bitcoin address raises an error."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "ckpool_mining"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"id": "miner", "btc_address": "", "ckpool_region": "solo.ckpool.org", "update_frequency": 5},
    )
    assert result["step_id"] == "mining_config"
    assert result["errors"]["base"] == "btc_address_required"


async def test_reconfigure_menu_add_mining(
    hass: HomeAssistant,
    bypass_setup: None,
) -> None:
    """The reconfigure menu can branch to adding a mining sensor."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "add_mining"})
    assert result["step_id"] == "select_mining_type"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"sensor_type": "btc_network"})
    assert result["step_id"] == "mining_config"


async def test_reauth_api_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Reauth surfaces an error when the API returns nothing."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", json=[])
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "api_error"


async def test_reconfigure_configure_mismatch(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """A multiplier mismatch during reconfigure raises an error."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "test",
            "multipliers": "1,2",
            "currency_name": "usd",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    assert result["step_id"] == "reconfigure_configure"
    assert result["errors"]["base"] == "mismatch_values"


async def test_reconfigure_add_new_crypto(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Searching merges an existing (unmatched) crypto and adds a new one."""
    entry = make_price_entry(cryptocurrency_ids="ethereum", multipliers="1")
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    assert result["step_id"] == "reconfigure_select"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"selected_cryptos": ["bitcoin", "ethereum"]}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "test",
            "multipliers": "1,1",
            "currency_name": "usd",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_removes_entity(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """A removed crypto's entity is deleted from the registry during reconfigure."""
    entry = make_price_entry(cryptocurrency_ids="bitcoin, ethereum", multipliers="1, 1")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_test_ethereum_usd") is not None

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": ""})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "test",
            "multipliers": "1",
            "currency_name": "usd",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    await hass.async_block_till_done()

    assert ent_reg.async_get_entity_id("sensor", DOMAIN, "cryptoinfo_test_ethereum_usd") is None


async def test_reconfigure_modify_price(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Modifying a price entry opens the search step."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    assert result["step_id"] == "reconfigure_price"


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """The reauth flow verifies connectivity and succeeds."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reconfigure_price_full(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Reconfiguring a price entry walks search -> select -> configure -> reload."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    assert result["step_id"] == "reconfigure_price"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    assert result["step_id"] == "reconfigure_select"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": ["bitcoin"]})
    assert result["step_id"] == "reconfigure_configure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "id": "test",
            "multipliers": "1",
            "currency_name": "usd",
            "unit_of_measurement": "$",
            "update_frequency": 5,
            "min_time_between_requests": 0,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_select_requires_choice(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """Reconfigure select rejects an empty selection."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search_query": "bitcoin"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"selected_cryptos": []})
    assert result["step_id"] == "reconfigure_select"
    assert result["errors"]["base"] == "no_crypto_selected"


async def test_reconfigure_mining_ckpool(
    hass: HomeAssistant,
    ckpool_config_entry: MockConfigEntry,
    bypass_setup: None,
) -> None:
    """Reconfiguring a CKPool entry updates its address."""
    ckpool_config_entry.add_to_hass(hass)
    result = await ckpool_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    assert result["step_id"] == "reconfigure_mining"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"id": "miner", "btc_address": "bc1qnew", "ckpool_region": "solo.ckpool.org", "update_frequency": 10},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_mining_network(
    hass: HomeAssistant,
    network_config_entry: MockConfigEntry,
    bypass_setup: None,
) -> None:
    """Reconfiguring a Bitcoin network entry updates its frequency."""
    network_config_entry.add_to_hass(hass)
    result = await network_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "modify"})
    assert result["step_id"] == "reconfigure_mining"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"id": "net", "update_frequency": 15},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_add_price(
    hass: HomeAssistant,
    mock_coingecko: AiohttpClientMocker,
    bypass_setup: None,
) -> None:
    """The reconfigure menu can branch to adding a price sensor."""
    entry = make_price_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"action": "add_price"})
    assert result["step_id"] == "price_search"


async def test_options_flow(
    hass: HomeAssistant,
    price_config_entry: MockConfigEntry,
    mock_coingecko: AiohttpClientMocker,
) -> None:
    """The options flow updates the update frequency."""
    price_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(price_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(price_config_entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"update_frequency": 10, "min_time_between_requests": 0.5},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert price_config_entry.options["update_frequency"] == 10
