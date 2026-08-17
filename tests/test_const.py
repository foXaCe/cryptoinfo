"""Test Cryptoinfo constants."""

from custom_components.cryptoinfo.const import DOMAIN


def test_domain_value() -> None:
    """Test domain constant value."""
    assert DOMAIN == "cryptoinfo"
    assert isinstance(DOMAIN, str)
