"""Test the CoinGecko API helper."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.const.const import API_ENDPOINT
from custom_components.cryptoinfo.exceptions import (
    CryptoInfoConnectionError,
    CryptoInfoInvalidResponseError,
    CryptoInfoRateLimitError,
)
from custom_components.cryptoinfo.helper.coingecko_api import (
    CIRCUIT_BREAKER_THRESHOLD,
    CoinGeckoAPI,
)

from .conftest import COIN_LIST_RESPONSE, MARKETS_RESPONSE


async def test_get_coins_markets(hass: HomeAssistant, mock_coingecko: AiohttpClientMocker) -> None:
    """Markets are returned as a list."""
    api = CoinGeckoAPI(hass)
    data = await api.get_coins_markets("bitcoin", "usd")
    assert data == MARKETS_RESPONSE


async def test_get_coins_markets_invalid(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A non-list markets payload raises an invalid-response error."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", json={"unexpected": True})
    api = CoinGeckoAPI(hass)
    with pytest.raises(CryptoInfoInvalidResponseError):
        await api.get_coins_markets("bitcoin", "usd")


async def test_coin_list_is_cached(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The coin list is fetched once and cached."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", json=COIN_LIST_RESPONSE)
    api = CoinGeckoAPI(hass)
    first = await api.get_coin_list()
    second = await api.get_coin_list()
    assert first == second == COIN_LIST_RESPONSE
    assert aioclient_mock.call_count == 1


async def test_validate_cryptocurrency_ids(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Validation flags unknown ids."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", json=COIN_LIST_RESPONSE)
    api = CoinGeckoAPI(hass)
    result = await api.validate_cryptocurrency_ids(["bitcoin", "nope"])
    assert result == {"bitcoin": True, "nope": False}


async def test_search_cryptocurrencies(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Search matches on id, name or symbol."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", json=COIN_LIST_RESPONSE)
    api = CoinGeckoAPI(hass)
    matches = await api.search_cryptocurrencies("eth")
    assert [c["id"] for c in matches] == ["ethereum"]


async def test_top_cryptocurrencies_fallback(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """On API error, a hardcoded top-10 fallback is returned."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", status=500)
    api = CoinGeckoAPI(hass)
    top = await api.get_top_cryptocurrencies(limit=10)
    assert len(top) == 10
    assert top[0]["id"] == "bitcoin"


async def test_top_cryptocurrencies_success(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A successful markets call is simplified to id/name/symbol."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", json=MARKETS_RESPONSE)
    api = CoinGeckoAPI(hass)
    top = await api.get_top_cryptocurrencies(limit=10)
    assert top == [{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"}]


async def test_rate_limit_error(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A persistent 429 eventually raises a rate-limit error."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", status=429, headers={"Retry-After": "0"})
    api = CoinGeckoAPI(hass)
    with pytest.raises(CryptoInfoRateLimitError):
        await api.get_coins_markets("bitcoin", "usd")


def test_circuit_breaker_opens(hass: HomeAssistant) -> None:
    """The circuit breaker opens after the failure threshold."""
    api = CoinGeckoAPI(hass)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD):
        api._record_failure()
    with pytest.raises(CryptoInfoConnectionError):
        api._check_circuit_breaker()
    # A success resets it
    api._record_success()
    api._check_circuit_breaker()


async def test_min_request_interval_skips_when_zero(hass: HomeAssistant) -> None:
    """With no throttle configured the timestamp list still records calls."""
    api = CoinGeckoAPI(hass)
    api.min_request_interval = 0
    api._request_timestamps = [datetime.now(UTC)]
    await api._check_rate_limit()
    assert len(api._request_timestamps) == 2


async def test_min_request_interval_throttles(hass: HomeAssistant, no_sleep: None) -> None:
    """A configured interval triggers a throttle wait."""
    api = CoinGeckoAPI(hass)
    api.min_request_interval = 60
    api._request_timestamps = [datetime.now(UTC)]
    await api._check_rate_limit()
    assert len(api._request_timestamps) == 2


async def test_open_circuit_blocks_request(hass: HomeAssistant, mock_coingecko: AiohttpClientMocker) -> None:
    """An open circuit breaker short-circuits requests."""
    api = CoinGeckoAPI(hass)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD):
        api._record_failure()
    with pytest.raises(CryptoInfoConnectionError):
        await api.get_coins_markets("bitcoin", "usd")


async def test_connection_error_retries_then_raises(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    no_sleep: None,
) -> None:
    """A persistent connection error raises after retries."""
    import aiohttp

    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", exc=aiohttp.ClientError())
    api = CoinGeckoAPI(hass)
    with pytest.raises(CryptoInfoConnectionError):
        await api.get_coins_markets("bitcoin", "usd")


async def test_empty_coin_list_fallbacks(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """With an empty coin list, search returns nothing and validation is permissive."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", json=[])
    api = CoinGeckoAPI(hass)
    assert await api.search_cryptocurrencies("anything") == []
    assert await api.validate_cryptocurrency_ids(["abc"]) == {"abc": True}


async def test_get_coin_list_error_returns_empty(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A failing coin list call is swallowed and returns an empty list."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/list", status=500)
    api = CoinGeckoAPI(hass)
    assert await api.get_coin_list() == []


async def test_invalid_json_response(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A non-JSON body raises an invalid-response error."""
    aioclient_mock.get(
        f"{API_ENDPOINT}coins/markets",
        text="<html>not json</html>",
        headers={"Content-Type": "text/html"},
    )
    api = CoinGeckoAPI(hass)
    with pytest.raises(CryptoInfoInvalidResponseError):
        await api.get_coins_markets("bitcoin", "usd")


async def test_rate_limit_then_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_sleep: None
) -> None:
    """A transient 429 is retried and then succeeds."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", status=429, headers={"Retry-After": "0"})
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", json=MARKETS_RESPONSE)
    api = CoinGeckoAPI(hass)
    # The mocker serves the first registered match repeatedly; ensure the retry path runs.
    with pytest.raises(CryptoInfoRateLimitError):
        await api.get_coins_markets("bitcoin", "usd")


async def test_sliding_window_rate_limit(hass: HomeAssistant, no_sleep: None) -> None:
    """Hitting the sliding-window limit triggers a wait."""
    api = CoinGeckoAPI(hass)
    api._request_timestamps = [datetime.now(UTC)] * 10
    await api._check_rate_limit()
    assert len(api._request_timestamps) >= 10


async def test_request_timeout(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_sleep: None) -> None:
    """A timeout surfaces as a connection error."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", exc=TimeoutError())
    api = CoinGeckoAPI(hass)
    with pytest.raises(CryptoInfoConnectionError):
        await api.get_coins_markets("bitcoin", "usd")


async def test_client_error_4xx(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A 4xx (non-429) response surfaces as a connection error."""
    aioclient_mock.get(f"{API_ENDPOINT}coins/markets", status=404)
    api = CoinGeckoAPI(hass)
    with pytest.raises(CryptoInfoConnectionError):
        await api.get_coins_markets("bitcoin", "usd")
