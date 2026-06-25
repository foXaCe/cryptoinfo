"""Exceptions for Cryptoinfo integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class CryptoInfoError(HomeAssistantError):
    """Base exception for Cryptoinfo integration."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize exception with optional status code."""
        super().__init__(message)
        self.status_code = status_code


class CryptoInfoConnectionError(CryptoInfoError):
    """Connection error (network issue, API down)."""


class CryptoInfoRateLimitError(CryptoInfoError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        """Initialize with retry_after hint."""
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class CryptoInfoInvalidResponseError(CryptoInfoError):
    """Invalid API response (bad JSON, unexpected format)."""
