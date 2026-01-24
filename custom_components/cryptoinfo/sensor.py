"""Sensor platform for Cryptoinfo integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const.const import (
    ATTR_1H_CHANGE,
    ATTR_1Y_CHANGE,
    ATTR_7D_CHANGE,
    ATTR_14D_CHANGE,
    ATTR_24H_CHANGE,
    ATTR_24H_VOLUME,
    ATTR_30D_CHANGE,
    ATTR_ATH,
    ATTR_ATH_CHANGE,
    ATTR_ATH_DATE,
    ATTR_BASE_PRICE,
    ATTR_CIRCULATING_SUPPLY,
    ATTR_CRYPTOCURRENCY_ID,
    ATTR_CRYPTOCURRENCY_NAME,
    ATTR_CRYPTOCURRENCY_SYMBOL,
    ATTR_CURRENCY_NAME,
    ATTR_IMAGE,
    ATTR_LAST_UPDATE,
    ATTR_MARKET_CAP,
    ATTR_MULTIPLIER,
    ATTR_RANK,
    ATTR_TOTAL_SUPPLY,
    CONF_CRYPTOCURRENCY_IDS,
    CONF_CURRENCY_NAME,
    CONF_ID,
    CONF_MIN_TIME_BETWEEN_REQUESTS,
    CONF_MULTIPLIERS,
    CONF_SENSOR_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
    SENSOR_PREFIX,
    SENSOR_TYPE_BTC_MEMPOOL,
    SENSOR_TYPE_BTC_NETWORK,
    SENSOR_TYPE_CKPOOL_MINING,
    SENSOR_TYPE_PRICE,
)
from .coordinator import CryptoDataCoordinator

if TYPE_CHECKING:
    from .const.const import CryptoInfoConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CryptoInfoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cryptoinfo sensor entities."""
    config = entry.data
    sensor_type = config.get(CONF_SENSOR_TYPE, SENSOR_TYPE_PRICE)

    # Route to mining sensors if applicable
    if sensor_type in [SENSOR_TYPE_BTC_NETWORK, SENSOR_TYPE_BTC_MEMPOOL, SENSOR_TYPE_CKPOOL_MINING]:
        from .mining_sensor import async_setup_mining_sensors

        await async_setup_mining_sensors(hass, config, async_add_entities)
        return

    # Price sensor setup
    _LOGGER.debug("Setting up Cryptoinfo price sensors for entry %s", entry.entry_id)

    id_name = (config.get(CONF_ID) or "").strip()
    cryptocurrency_ids = config.get(CONF_CRYPTOCURRENCY_IDS, "").lower().strip()
    currency_name = config.get(CONF_CURRENCY_NAME, "").strip()
    unit_of_measurement = (config.get(CONF_UNIT_OF_MEASUREMENT) or "").strip()
    multipliers = config.get(CONF_MULTIPLIERS, "1").strip()
    update_frequency = timedelta(minutes=float(config.get(CONF_UPDATE_FREQUENCY, 5)))
    min_time_between_requests = timedelta(minutes=float(config.get(CONF_MIN_TIME_BETWEEN_REQUESTS, 0.25)))

    # Create coordinator
    coordinator = CryptoDataCoordinator(
        hass,
        cryptocurrency_ids,
        currency_name,
        update_frequency,
        min_time_between_requests,
        id_name,
    )

    # Store coordinator in runtime_data
    entry.runtime_data.coordinator = coordinator
    entry.runtime_data.coordinators[entry.entry_id] = coordinator

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Create entities
    crypto_list = [crypto.strip() for crypto in cryptocurrency_ids.split(",")]
    multipliers_list = [mult.strip() for mult in multipliers.split(",")]

    if len(crypto_list) != len(multipliers_list):
        _LOGGER.error(
            "Length mismatch: %d cryptocurrencies but %d multipliers",
            len(crypto_list),
            len(multipliers_list),
        )
        return

    entities = [
        CryptoinfoSensor(
            coordinator=coordinator,
            cryptocurrency_id=crypto_id,
            currency_name=currency_name,
            unit_of_measurement=unit_of_measurement,
            multiplier=multipliers_list[i],
            id_name=id_name,
        )
        for i, crypto_id in enumerate(crypto_list)
    ]

    async_add_entities(entities)


class CryptoinfoSensor(CoordinatorEntity[CryptoDataCoordinator], SensorEntity):
    """Cryptocurrency price sensor."""

    __slots__ = ("_id_name", "cryptocurrency_id", "currency_name", "multiplier")

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:bitcoin"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: CryptoDataCoordinator,
        cryptocurrency_id: str,
        currency_name: str,
        unit_of_measurement: str,
        multiplier: str,
        id_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.cryptocurrency_id = cryptocurrency_id
        self.currency_name = currency_name
        self.multiplier = multiplier
        self._id_name = id_name

        # Entity attributes
        self._attr_native_unit_of_measurement = unit_of_measurement or None
        self._attr_translation_key = "crypto_price"

        # Entity naming
        self._attr_name = f"{cryptocurrency_id.capitalize()} {currency_name.upper()}"
        if id_name:
            self._attr_name = f"{id_name} {self._attr_name}"

        # Unique ID
        self._attr_unique_id = f"{SENSOR_PREFIX}{id_name}_{cryptocurrency_id}_{currency_name}".lower().replace(" ", "_")

        # Device info (enables device grouping in HA)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"cryptoinfo_{id_name or 'default'}")},
            name=f"Cryptoinfo {id_name or 'Wallet'}",
            manufacturer="CoinGecko",
            model="Cryptocurrency Tracker",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        return self.cryptocurrency_id in self.coordinator.data

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        if not self.coordinator.data:
            return None
        coin_data = self.coordinator.data.get(self.cryptocurrency_id)
        if not coin_data:
            return None
        try:
            return float(coin_data["current_price"]) * float(self.multiplier)
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return self._empty_attributes()

        data = self.coordinator.data.get(self.cryptocurrency_id)
        if not data:
            return self._empty_attributes()

        return {
            ATTR_LAST_UPDATE: datetime.now().strftime("%d-%m-%Y %H:%M"),
            ATTR_CRYPTOCURRENCY_ID: self.cryptocurrency_id,
            ATTR_CRYPTOCURRENCY_NAME: data.get("name"),
            ATTR_CRYPTOCURRENCY_SYMBOL: data.get("symbol"),
            ATTR_CURRENCY_NAME: self.currency_name,
            ATTR_BASE_PRICE: data.get("current_price"),
            ATTR_MULTIPLIER: self.multiplier,
            ATTR_24H_VOLUME: data.get("total_volume"),
            ATTR_1H_CHANGE: data.get("price_change_percentage_1h_in_currency"),
            ATTR_24H_CHANGE: data.get("price_change_percentage_24h_in_currency"),
            ATTR_7D_CHANGE: data.get("price_change_percentage_7d_in_currency"),
            ATTR_14D_CHANGE: data.get("price_change_percentage_14d_in_currency"),
            ATTR_30D_CHANGE: data.get("price_change_percentage_30d_in_currency"),
            ATTR_1Y_CHANGE: data.get("price_change_percentage_1y_in_currency"),
            ATTR_MARKET_CAP: data.get("market_cap"),
            ATTR_CIRCULATING_SUPPLY: data.get("circulating_supply"),
            ATTR_TOTAL_SUPPLY: data.get("total_supply"),
            ATTR_ATH: data.get("ath"),
            ATTR_ATH_DATE: data.get("ath_date"),
            ATTR_ATH_CHANGE: data.get("ath_change_percentage"),
            ATTR_RANK: data.get("market_cap_rank"),
            ATTR_IMAGE: data.get("image"),
        }

    def _empty_attributes(self) -> dict[str, Any]:
        """Return empty attributes when no data available."""
        return {
            ATTR_LAST_UPDATE: datetime.now().strftime("%d-%m-%Y %H:%M"),
            ATTR_CRYPTOCURRENCY_NAME: None,
            ATTR_CURRENCY_NAME: None,
            ATTR_BASE_PRICE: None,
            ATTR_MULTIPLIER: None,
            ATTR_24H_VOLUME: None,
            ATTR_1H_CHANGE: None,
            ATTR_24H_CHANGE: None,
            ATTR_7D_CHANGE: None,
            ATTR_14D_CHANGE: None,
            ATTR_30D_CHANGE: None,
            ATTR_1Y_CHANGE: None,
            ATTR_MARKET_CAP: None,
            ATTR_CIRCULATING_SUPPLY: None,
            ATTR_TOTAL_SUPPLY: None,
            ATTR_ATH: None,
            ATTR_ATH_DATE: None,
            ATTR_ATH_CHANGE: None,
            ATTR_RANK: None,
            ATTR_IMAGE: None,
        }
