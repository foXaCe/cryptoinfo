#!/usr/bin/env python3
"""Mining sensor components for Cryptoinfo.

Author: foXaCe
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

if TYPE_CHECKING:
    from typing import Any

    from homeassistant.core import HomeAssistant

from .const.const import (
    _LOGGER,
    CONF_BTC_ADDRESS,
    CONF_ID,
    CONF_SENSOR_TYPE,
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
    SENSOR_PREFIX,
    SENSOR_TYPE_BTC_MEMPOOL,
    SENSOR_TYPE_BTC_NETWORK,
    SENSOR_TYPE_CKPOOL_MINING,
)
from .helper.blockchain_api import BlockchainAPI, CKPoolAPI

# Default timeout for API requests (seconds)
DEFAULT_TIMEOUT = 30


async def async_setup_mining_sensors(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up mining sensors based on sensor type."""
    sensor_type = config.get(CONF_SENSOR_TYPE)
    id_name = config.get(CONF_ID, "").strip()
    update_frequency = timedelta(minutes=float(config.get(CONF_UPDATE_FREQUENCY, 5)))

    if sensor_type == SENSOR_TYPE_BTC_NETWORK:
        coordinator = BTCNetworkCoordinator(hass, update_frequency)
        await coordinator.async_config_entry_first_refresh()
        async_add_entities([BTCNetworkSensor(coordinator, id_name)])

    elif sensor_type == SENSOR_TYPE_BTC_MEMPOOL:
        coordinator = BTCMempoolCoordinator(hass, update_frequency)
        await coordinator.async_config_entry_first_refresh()
        async_add_entities([BTCMempoolSensor(coordinator, id_name)])

    elif sensor_type == SENSOR_TYPE_CKPOOL_MINING:
        from .const.const import CKPOOL_REGION_EU, CONF_CKPOOL_REGION

        btc_address = config.get(CONF_BTC_ADDRESS, "").strip()
        if not btc_address:
            _LOGGER.error("BTC address is required for CKPool mining sensor")
            return False
        pool_region = config.get(CONF_CKPOOL_REGION, CKPOOL_REGION_EU)
        coordinator = CKPoolCoordinator(hass, btc_address, pool_region, update_frequency)
        await coordinator.async_config_entry_first_refresh()
        async_add_entities([CKPoolMiningSensor(coordinator, id_name, btc_address)])

    return True


class BTCNetworkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Bitcoin network statistics."""

    def __init__(self, hass: HomeAssistant, update_interval: timedelta) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Bitcoin Network Stats",
            update_interval=update_interval,
        )
        self.api = BlockchainAPI(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from blockchain API."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                data = await self.api.get_network_stats()
                return data or {}
        except TimeoutError as err:
            raise UpdateFailed("Request timeout") from err


class BTCMempoolCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Bitcoin mempool statistics."""

    def __init__(self, hass: HomeAssistant, update_interval: timedelta) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Bitcoin Mempool Stats",
            update_interval=update_interval,
        )
        self.api = BlockchainAPI(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from mempool API."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                data = await self.api.get_mempool_stats()
                return data or {}
        except TimeoutError as err:
            raise UpdateFailed("Request timeout") from err


class CKPoolCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch CKPool mining statistics."""

    def __init__(self, hass: HomeAssistant, btc_address: str, pool_region: str, update_interval: timedelta) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"CKPool Stats {btc_address[:8]}...",
            update_interval=update_interval,
        )
        self.api = CKPoolAPI(hass, pool_region)
        self.btc_address = btc_address

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from CKPool API."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                data = await self.api.get_user_stats(self.btc_address)
                return data or {}
        except TimeoutError as err:
            raise UpdateFailed("Request timeout") from err


class BTCNetworkSensor(CoordinatorEntity[BTCNetworkCoordinator], SensorEntity):
    """Bitcoin Network Statistics Sensor."""

    __slots__ = ()

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "btc_network"
    _attr_icon = "mdi:bitcoin"
    _attr_native_unit_of_measurement = "EH/s"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: BTCNetworkCoordinator, id_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{id_name} Bitcoin Network" if id_name else "Bitcoin Network"
        self._attr_unique_id = f"{SENSOR_PREFIX}btc_network_{id_name}".lower().replace(" ", "_")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "btc_network")},
            name="Bitcoin Network",
            manufacturer="Bitcoin",
            model="Network Statistics",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and bool(self.coordinator.data)

    @property
    def native_value(self) -> float | None:
        """Return the hashrate as the main value."""
        if self.coordinator.data:
            return round(self.coordinator.data.get("hashrate", 0), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        return {
            "difficulty": data.get("difficulty", 0),
            "block_height": data.get("block_height", 0),
            "next_difficulty_block": data.get("next_difficulty_block", 0),
            "blocks_until_retarget": data.get("blocks_until_retarget", 0),
            "difficulty_change": f"{data.get('difficulty_change', 0):.2f}%",
            "next_halving_block": data.get("next_halving_block", 0),
            "blocks_until_halving": data.get("blocks_until_halving", 0),
        }


class BTCMempoolSensor(CoordinatorEntity[BTCMempoolCoordinator], SensorEntity):
    """Bitcoin Mempool Statistics Sensor."""

    __slots__ = ()

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "btc_mempool"
    _attr_icon = "mdi:database"
    _attr_native_unit_of_measurement = "txs"

    def __init__(self, coordinator: BTCMempoolCoordinator, id_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{id_name} Bitcoin Mempool" if id_name else "Bitcoin Mempool"
        self._attr_unique_id = f"{SENSOR_PREFIX}btc_mempool_{id_name}".lower().replace(" ", "_")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "btc_mempool")},
            name="Bitcoin Mempool",
            manufacturer="Bitcoin",
            model="Mempool Statistics",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and bool(self.coordinator.data)

    @property
    def native_value(self) -> int | None:
        """Return the mempool size as the main value."""
        if self.coordinator.data:
            return self.coordinator.data.get("mempool_size", 0)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        return {
            "mempool_mb": round(data.get("mempool_bytes", 0), 2),
            "fee_fastest": f"{data.get('fee_fastest', 0)} sat/vB",
            "fee_half_hour": f"{data.get('fee_half_hour', 0)} sat/vB",
            "fee_hour": f"{data.get('fee_hour', 0)} sat/vB",
            "fee_economy": f"{data.get('fee_economy', 0)} sat/vB",
            "fee_minimum": f"{data.get('fee_minimum', 0)} sat/vB",
        }


class CKPoolMiningSensor(CoordinatorEntity[CKPoolCoordinator], SensorEntity):
    """CKPool Solo Mining Statistics Sensor."""

    __slots__ = ("btc_address",)

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "ckpool_mining"
    _attr_icon = "mdi:pickaxe"
    _attr_native_unit_of_measurement = "GH/s"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: CKPoolCoordinator, id_name: str, btc_address: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{id_name} CKPool Mining" if id_name else "CKPool Mining"
        self._attr_unique_id = f"{SENSOR_PREFIX}ckpool_{btc_address[:8]}".lower().replace(" ", "_")
        self.btc_address = btc_address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ckpool_{btc_address[:8]}")},
            name=f"CKPool Mining {btc_address[:8]}...",
            manufacturer="CKPool",
            model="Solo Mining",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and bool(self.coordinator.data)

    @property
    def native_value(self) -> float | None:
        """Return the hashrate as the main value."""
        if self.coordinator.data:
            return round(self.coordinator.data.get("hashrate", 0), 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data

        # Format best_share for display
        best_share = data.get("best_share", 0)
        if best_share > 1e9:
            best_share_display = f"{best_share / 1e9:.2f} G"
        elif best_share > 1e6:
            best_share_display = f"{best_share / 1e6:.2f} M"
        else:
            best_share_display = f"{best_share:.0f}"

        # Format best_ever for display
        best_ever = data.get("best_ever", 0)
        if best_ever > 1e9:
            best_ever_display = f"{best_ever / 1e9:.2f} G"
        elif best_ever > 1e6:
            best_ever_display = f"{best_ever / 1e6:.2f} M"
        else:
            best_ever_display = f"{best_ever:.0f}"

        return {
            "btc_address": self.btc_address,
            "hashrate_1h": round(data.get("hashrate_1h", 0), 2),
            "hashrate_24h": round(data.get("hashrate_24h", 0), 2),
            "best_share": best_share_display,
            "best_ever": best_ever_display,
            "workers": data.get("workers", 0),
            "blocks_found": data.get("blocks_found", 0),
        }
