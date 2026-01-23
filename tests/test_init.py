"""Test Cryptoinfo integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.cryptoinfo.const.const import (
    DOMAIN,
    CryptoInfoRuntimeData,
)


async def test_domain_constant() -> None:
    """Test that the domain constant is correctly defined."""
    assert DOMAIN == "cryptoinfo"


async def test_async_setup_entry_creates_runtime_data(
    hass: HomeAssistant,
    mock_coingecko_api: AsyncMock,
) -> None:
    """Test that async_setup_entry creates runtime_data on the entry."""
    with patch(f"custom_components.{DOMAIN}.CryptoInfoData") as mock_data_class:
        mock_data = AsyncMock()
        mock_data.async_initialize = AsyncMock()
        mock_data.store = AsyncMock()
        mock_data_class.return_value = mock_data

        # Import here to avoid import errors before patches
        from custom_components.cryptoinfo import async_setup_entry

        # Create a mock config entry
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.add_update_listener = MagicMock(return_value=lambda: None)
        mock_entry.async_on_unload = MagicMock()
        mock_entry.runtime_data = None

        with patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            return_value=None,
        ):
            result = await async_setup_entry(hass, mock_entry)

        assert result is True
        # Verify runtime_data was set on the entry
        assert mock_entry.runtime_data is not None
        assert isinstance(mock_entry.runtime_data, CryptoInfoRuntimeData)
        assert mock_entry.runtime_data.shared_data is mock_data


async def test_async_unload_entry(
    hass: HomeAssistant,
) -> None:
    """Test that async_unload_entry properly unloads."""
    from custom_components.cryptoinfo import async_unload_entry

    # Setup mock runtime_data
    mock_store = AsyncMock()
    mock_shared_data = AsyncMock()
    mock_shared_data.store = mock_store

    mock_runtime_data = CryptoInfoRuntimeData(
        shared_data=mock_shared_data,
        coordinator=None,
        coordinators={},
    )

    # Create a mock config entry with runtime_data
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_entry.runtime_data = mock_runtime_data

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_entry)

    assert result is True
    mock_store.async_save.assert_called_once()
