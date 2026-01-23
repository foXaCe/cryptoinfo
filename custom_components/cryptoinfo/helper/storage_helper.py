"""Storage helper for CryptoInfo."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "cryptoinfo_data"


class CryptoInfoStore:
    """Class to hold CryptoInfo data."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the store."""
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data = {"min_time_between_requests": 1.0}

    async def async_load(self) -> None:
        """Load the data from storage."""
        stored = await self.store.async_load()
        if stored:
            self.data = stored

    async def async_save(self) -> None:
        """Save data to storage."""
        await self.store.async_save(self.data)
