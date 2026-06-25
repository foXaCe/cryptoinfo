"""Fixtures for Cryptoinfo tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const.const import (
    API_ENDPOINT,
    CONF_BTC_ADDRESS,
    CONF_CKPOOL_REGION,
    CONF_CRYPTOCURRENCY_IDS,
    CONF_CURRENCY_NAME,
    CONF_ID,
    CONF_MIN_TIME_BETWEEN_REQUESTS,
    CONF_MULTIPLIERS,
    CONF_SENSOR_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
    SENSOR_TYPE_BTC_MEMPOOL,
    SENSOR_TYPE_BTC_NETWORK,
    SENSOR_TYPE_CKPOOL_MINING,
    SENSOR_TYPE_PRICE,
)

MEMPOOL_SPACE_API = "https://mempool.space/api"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Generator[None]:
    """Enable loading of custom integrations in all tests."""
    return


@pytest.fixture
def no_sleep() -> Generator[None]:
    """Skip retry/backoff sleeps in the API helpers to keep tests fast."""
    with (
        patch("custom_components.cryptoinfo.helper.coingecko_api.asyncio.sleep", AsyncMock()),
        patch("custom_components.cryptoinfo.helper.blockchain_api.asyncio.sleep", AsyncMock()),
    ):
        yield


# --- Sample API payloads --------------------------------------------------

MARKETS_RESPONSE: list[dict[str, Any]] = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "image": "https://example.com/btc.png",
        "current_price": 50000.0,
        "market_cap": 950000000000,
        "market_cap_rank": 1,
        "total_volume": 30000000000,
        "price_change_percentage_1h_in_currency": 0.5,
        "price_change_percentage_24h_in_currency": 2.5,
        "price_change_percentage_7d_in_currency": -1.0,
        "price_change_percentage_14d_in_currency": 3.0,
        "price_change_percentage_30d_in_currency": 10.0,
        "price_change_percentage_1y_in_currency": 100.0,
        "circulating_supply": 19000000,
        "total_supply": 21000000,
        "ath": 69000,
        "ath_date": "2021-11-10T00:00:00.000Z",
        "ath_change_percentage": -27.0,
    },
]

COIN_LIST_RESPONSE: list[dict[str, Any]] = [
    {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
]


def make_price_entry(**overrides: Any) -> MockConfigEntry:
    """Build a price MockConfigEntry."""
    data = {
        CONF_SENSOR_TYPE: SENSOR_TYPE_PRICE,
        CONF_ID: "test",
        CONF_CRYPTOCURRENCY_IDS: "bitcoin",
        CONF_CURRENCY_NAME: "usd",
        CONF_MULTIPLIERS: "1",
        CONF_UNIT_OF_MEASUREMENT: "$",
        CONF_UPDATE_FREQUENCY: 5,
        CONF_MIN_TIME_BETWEEN_REQUESTS: 0,
    }
    data.update(overrides)
    return MockConfigEntry(domain=DOMAIN, title="Cryptoinfo - Test", data=data, unique_id="test")


@pytest.fixture
def price_config_entry() -> MockConfigEntry:
    """Return a mock price config entry."""
    return make_price_entry()


@pytest.fixture
def network_config_entry() -> MockConfigEntry:
    """Return a mock Bitcoin network config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Bitcoin Network",
        data={CONF_SENSOR_TYPE: SENSOR_TYPE_BTC_NETWORK, CONF_ID: "", CONF_UPDATE_FREQUENCY: 5},
        unique_id="btc_network_",
    )


@pytest.fixture
def mempool_config_entry() -> MockConfigEntry:
    """Return a mock Bitcoin mempool config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Bitcoin Mempool",
        data={CONF_SENSOR_TYPE: SENSOR_TYPE_BTC_MEMPOOL, CONF_ID: "", CONF_UPDATE_FREQUENCY: 5},
        unique_id="btc_mempool_",
    )


@pytest.fixture
def ckpool_config_entry() -> MockConfigEntry:
    """Return a mock CKPool config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="CKPool Mining",
        data={
            CONF_SENSOR_TYPE: SENSOR_TYPE_CKPOOL_MINING,
            CONF_ID: "",
            CONF_BTC_ADDRESS: "bc1qexampleaddress0000000000000000000000",
            CONF_CKPOOL_REGION: "solo.ckpool.org",
            CONF_UPDATE_FREQUENCY: 5,
        },
        unique_id="ckpool_mining_",
    )


@pytest.fixture
def mock_coingecko(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock the CoinGecko endpoints used by the integration."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", json=MARKETS_RESPONSE)
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", json=COIN_LIST_RESPONSE)
    return aioclient_mock


@pytest.fixture
def mock_mempool(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock the mempool.space endpoints used by the mining sensors."""
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/v1/mining/hashrate/3d", json={"currentHashrate": 6e20})
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/blocks/tip/height", text="870000")
    aioclient_mock.get(
        f"{MEMPOOL_SPACE_API}/v1/difficulty-adjustment",
        json={
            "difficulty": 1.0e14,
            "nextRetargetHeight": 870016,
            "remainingBlocks": 16,
            "difficultyChange": 1.23,
        },
    )
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/mempool", json={"count": 12000, "vsize": 5_000_000})
    aioclient_mock.get(
        f"{MEMPOOL_SPACE_API}/v1/fees/recommended",
        json={"fastestFee": 20, "halfHourFee": 15, "hourFee": 10, "economyFee": 5, "minimumFee": 1},
    )
    return aioclient_mock
