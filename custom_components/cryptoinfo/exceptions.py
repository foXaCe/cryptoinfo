"""Exceptions for Cryptoinfo integration."""

from homeassistant.exceptions import HomeAssistantError


class CryptoInfoError(HomeAssistantError):
    """Base exception for Cryptoinfo integration."""


class CryptoInfoAuthError(CryptoInfoError):
    """Authentication error (API key invalid, rate limited)."""


class CryptoInfoConnectionError(CryptoInfoError):
    """Connection error (network issue, API down)."""


class CryptoInfoApiError(CryptoInfoError):
    """API error (invalid response, parsing error)."""
