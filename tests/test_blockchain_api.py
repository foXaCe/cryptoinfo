"""Test the blockchain / mempool / CKPool API helpers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.cryptoinfo.helper.blockchain_api import (
    BlockchainAPI,
    CKPoolAPI,
)

from .conftest import MEMPOOL_SPACE_API


async def test_network_stats(hass: HomeAssistant, mock_mempool: AiohttpClientMocker) -> None:
    """Network stats are aggregated and converted to EH/s."""
    api = BlockchainAPI(hass)
    data = await api.get_network_stats()
    assert data is not None
    assert data["hashrate"] == 600.0
    assert data["block_height"] == 870000


async def test_network_stats_error_returns_none(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """If one parallel request fails, network stats return None."""
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/v1/mining/hashrate/3d", json={"currentHashrate": 6e20})
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/blocks/tip/height", text="870000")
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/v1/difficulty-adjustment", status=500)
    api = BlockchainAPI(hass)
    assert await api.get_network_stats() is None


async def test_mempool_stats(hass: HomeAssistant, mock_mempool: AiohttpClientMocker) -> None:
    """Mempool stats expose tx count and fees."""
    api = BlockchainAPI(hass)
    data = await api.get_mempool_stats()
    assert data is not None
    assert data["mempool_size"] == 12000
    assert data["fee_fastest"] == 20


async def test_ckpool_404_returns_empty(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A 404 (no mining history) returns a zeroed payload."""
    aioclient_mock.get("https://solo.ckpool.org/users/addr", status=404)
    api = CKPoolAPI(hass, "solo.ckpool.org")
    data = await api.get_user_stats("addr")
    assert data == {
        "hashrate": 0,
        "hashrate_1h": 0,
        "hashrate_24h": 0,
        "best_share": 0,
        "best_ever": 0,
        "workers": 0,
        "blocks_found": 0,
    }


async def test_ckpool_html_eu_pool(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """The EU pool returns HTML with embedded escaped JSON that is parsed."""
    html = (
        'x \\"hashrate1m\\":\\"1060000000000\\" '
        '\\"hashrate1hr\\":\\"1000000000000\\" '
        '\\"hashrate1d\\":\\"900000000000\\" '
        '\\"workers\\":[{\\"id\\":\\"w1\\"},{\\"id\\":\\"w2\\"}] '
        '\\"bestShare\\":1234.5 \\"bestEver\\":\\"99999\\" y'
    )
    aioclient_mock.get(
        "https://eusolostats.ckpool.org/users/addr",
        text=html,
        headers={"Content-Type": "text/html"},
    )
    api = CKPoolAPI(hass, "eusolostats.ckpool.org")
    data = await api.get_user_stats("addr")
    assert data is not None
    assert data["hashrate"] == 1060.0
    assert data["workers"] == 2


def test_extract_json_from_html_returns_none_on_garbage(hass: HomeAssistant) -> None:
    """Unparsable HTML yields None."""
    api = CKPoolAPI(hass)
    assert api._extract_json_from_html("<html>nothing useful</html>") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3.12T", 3120.0),
        ("5G", 5.0),
        ("100M", 0.1),
        ("2K", 0.0),
        ("1000000000", 1.0),
        (3.5, 0.0),
        ("not-a-number", 0.0),
        (1_060_000_000_000, 1060.0),
        ("0", 0.0),
        (0, 0.0),
        (None, 0.0),
    ],
)
def test_parse_ckpool_hashrate(hass: HomeAssistant, raw: object, expected: float) -> None:
    """Hashrate parsing handles both string-with-unit and integer formats."""
    api = CKPoolAPI(hass)
    parsed = api._parse_ckpool_data({"hashrate1m": raw})
    assert parsed["hashrate"] == expected


async def test_ckpool_unexpected_content_type(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """An unexpected content type results in no data."""
    aioclient_mock.get(
        "https://solo.ckpool.org/users/addr",
        text="oops",
        headers={"Content-Type": "text/plain"},
    )
    api = CKPoolAPI(hass, "solo.ckpool.org")
    assert await api.get_user_stats("addr") is None


async def test_ckpool_circuit_breaker_open(hass: HomeAssistant) -> None:
    """An open circuit breaker blocks CKPool requests."""
    from custom_components.cryptoinfo.exceptions import CryptoInfoConnectionError

    api = CKPoolAPI(hass, "solo.ckpool.org")
    for _ in range(5):
        api._record_failure()
    with pytest.raises(CryptoInfoConnectionError):
        await api.get_user_stats("addr")


async def test_ckpool_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    no_sleep: None,
) -> None:
    """A persistent connection error returns None after retries."""
    import aiohttp

    aioclient_mock.get("https://solo.ckpool.org/users/addr", exc=aiohttp.ClientError())
    api = CKPoolAPI(hass, "solo.ckpool.org")
    assert await api.get_user_stats("addr") is None


async def test_ckpool_http_error(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A non-404 HTTP error surfaces as a connection error."""
    from custom_components.cryptoinfo.exceptions import CryptoInfoConnectionError

    aioclient_mock.get("https://solo.ckpool.org/users/addr", status=400)
    api = CKPoolAPI(hass, "solo.ckpool.org")
    with pytest.raises(CryptoInfoConnectionError):
        await api.get_user_stats("addr")


async def test_ckpool_html_unparsable(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """HTML that cannot be parsed yields no data."""
    aioclient_mock.get(
        "https://eusolostats.ckpool.org/users/addr",
        text="<html>no json here</html>",
        headers={"Content-Type": "text/html"},
    )
    api = CKPoolAPI(hass, "eusolostats.ckpool.org")
    assert await api.get_user_stats("addr") is None


async def test_network_stats_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    no_sleep: None,
) -> None:
    """Connection errors during the parallel network fetch yield None."""
    import aiohttp

    for path in ("v1/mining/hashrate/3d", "blocks/tip/height", "v1/difficulty-adjustment"):
        aioclient_mock.get(f"{MEMPOOL_SPACE_API}/{path}", exc=aiohttp.ClientError())
    api = BlockchainAPI(hass)
    assert await api.get_network_stats() is None


async def test_mempool_stats_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    no_sleep: None,
) -> None:
    """Connection errors during the mempool fetch yield None."""
    import aiohttp

    for path in ("mempool", "v1/fees/recommended"):
        aioclient_mock.get(f"{MEMPOOL_SPACE_API}/{path}", exc=aiohttp.ClientError())
    api = BlockchainAPI(hass)
    assert await api.get_mempool_stats() is None


def test_blockchain_circuit_breaker(hass: HomeAssistant) -> None:
    """The BlockchainAPI circuit breaker opens after repeated failures."""
    from custom_components.cryptoinfo.exceptions import CryptoInfoConnectionError

    api = BlockchainAPI(hass)
    for _ in range(5):
        api._record_failure()
    with pytest.raises(CryptoInfoConnectionError):
        api._check_circuit_breaker()


async def test_network_timeout(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_sleep: None) -> None:
    """Timeouts during the network fetch yield None."""
    for path in ("v1/mining/hashrate/3d", "blocks/tip/height", "v1/difficulty-adjustment"):
        aioclient_mock.get(f"{MEMPOOL_SPACE_API}/{path}", exc=TimeoutError())
    api = BlockchainAPI(hass)
    assert await api.get_network_stats() is None


async def test_network_bad_height(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A non-numeric block height is handled and returns None."""
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/v1/mining/hashrate/3d", json={"currentHashrate": 6e20})
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/blocks/tip/height", text="not-a-number")
    aioclient_mock.get(
        f"{MEMPOOL_SPACE_API}/v1/difficulty-adjustment",
        json={"difficulty": 1.0, "nextRetargetHeight": 1, "remainingBlocks": 1, "difficultyChange": 0.0},
    )
    api = BlockchainAPI(hass)
    assert await api.get_network_stats() is None


async def test_mempool_bad_data(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A malformed mempool payload is handled and returns None."""
    aioclient_mock.get(f"{MEMPOOL_SPACE_API}/mempool", json={"count": 10, "vsize": "oops"})
    aioclient_mock.get(
        f"{MEMPOOL_SPACE_API}/v1/fees/recommended",
        json={"fastestFee": 1, "halfHourFee": 1, "hourFee": 1, "economyFee": 1, "minimumFee": 1},
    )
    api = BlockchainAPI(hass)
    assert await api.get_mempool_stats() is None


async def test_ckpool_timeout(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_sleep: None) -> None:
    """A CKPool timeout returns None after retries."""
    aioclient_mock.get("https://solo.ckpool.org/users/addr", exc=TimeoutError())
    api = CKPoolAPI(hass, "solo.ckpool.org")
    assert await api.get_user_stats("addr") is None
