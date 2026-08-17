"""Sensor platform for Cryptoinfo integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CRYPTOCURRENCY_ID,
    ATTR_CRYPTOCURRENCY_NAME,
    ATTR_CRYPTOCURRENCY_SYMBOL,
    ATTR_CURRENCY_NAME,
    ATTR_IMAGE,
    ATTR_MULTIPLIER,
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
from .coordinator import CryptoDataCoordinator
from .helpers import build_price_unique_id
from .sensor_descriptions import (
    PRICE_DESCRIPTIONS,
    CryptoSensorEntityDescription,
    resolve_price_unit,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .const import CryptoInfoConfigEntry

_LOGGER = logging.getLogger(__name__)

# Coordinator-driven entities do not perform their own I/O.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CryptoInfoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cryptoinfo sensor entities."""
    # Options take precedence over the original config data.
    config: dict[str, Any] = {**entry.data, **entry.options}
    sensor_type = config.get(CONF_SENSOR_TYPE, SENSOR_TYPE_PRICE)

    # Route to mining sensors if applicable
    if sensor_type in (SENSOR_TYPE_BTC_NETWORK, SENSOR_TYPE_BTC_MEMPOOL, SENSOR_TYPE_CKPOOL_MINING):
        from .mining_sensor import async_setup_mining_sensors

        await async_setup_mining_sensors(hass, config, async_add_entities)
        return

    # Price sensor setup
    _LOGGER.debug("Setting up Cryptoinfo price sensors for entry %s", entry.entry_id)

    shared = entry.runtime_data.shared_data

    id_name = (config.get(CONF_ID) or "").strip()
    cryptocurrency_ids = config.get(CONF_CRYPTOCURRENCY_IDS, "").lower().strip()
    currency_name = config.get(CONF_CURRENCY_NAME, "").strip()
    unit_of_measurement = (config.get(CONF_UNIT_OF_MEASUREMENT) or "").strip()
    multipliers = config.get(CONF_MULTIPLIERS, "1").strip()
    update_frequency = timedelta(minutes=float(config.get(CONF_UPDATE_FREQUENCY, 5)))
    min_time = float(config.get(CONF_MIN_TIME_BETWEEN_REQUESTS, shared.min_time_between_requests))

    # Apply the (shared) minimum delay between CoinGecko requests.
    shared.api.min_request_interval = min_time * 60

    coordinator = CryptoDataCoordinator(
        hass,
        shared.api,
        cryptocurrency_ids,
        currency_name,
        update_frequency,
        id_name,
    )

    # Store coordinator in runtime_data
    entry.runtime_data.coordinator = coordinator
    entry.runtime_data.coordinators[entry.entry_id] = coordinator

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Create entities
    crypto_list = [crypto.strip() for crypto in cryptocurrency_ids.split(",") if crypto.strip()]
    multipliers_list = [mult.strip() for mult in multipliers.split(",")]

    if len(crypto_list) != len(multipliers_list):
        _LOGGER.error(
            "Length mismatch: %d cryptocurrencies but %d multipliers",
            len(crypto_list),
            len(multipliers_list),
        )
        return

    entities: list[SensorEntity] = []
    for i, crypto_id in enumerate(crypto_list):
        entities.append(
            CryptoinfoSensor(
                coordinator=coordinator,
                cryptocurrency_id=crypto_id,
                currency_name=currency_name,
                unit_of_measurement=unit_of_measurement,
                multiplier=multipliers_list[i],
                id_name=id_name,
            )
        )
        base_unique_id = build_price_unique_id(id_name, crypto_id, currency_name)
        for description in PRICE_DESCRIPTIONS:
            entities.append(
                CryptoinfoDerivedSensor(
                    coordinator=coordinator,
                    description=description,
                    cryptocurrency_id=crypto_id,
                    currency_name=currency_name,
                    unit_of_measurement=unit_of_measurement,
                    base_unique_id=base_unique_id,
                    id_name=id_name,
                )
            )

    async_add_entities(entities)


class CryptoinfoSensor(CoordinatorEntity[CryptoDataCoordinator], SensorEntity):
    """Cryptocurrency price sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "crypto_price"
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
        self._attr_translation_placeholders = {
            "cryptocurrency": cryptocurrency_id.capitalize(),
            "currency": currency_name.upper(),
        }

        # Unique ID (stable across renames; currency + id_name keep it unique)
        self._attr_unique_id = build_price_unique_id(id_name, cryptocurrency_id, currency_name)

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
        return bool(
            self.coordinator.last_update_success
            and self.coordinator.data
            and self.cryptocurrency_id in self.coordinator.data
        )

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
        """Return identity attributes (metrics are exposed as entities)."""
        data = self.coordinator.data.get(self.cryptocurrency_id) if self.coordinator.data else None
        if not data:
            return {
                ATTR_CRYPTOCURRENCY_ID: self.cryptocurrency_id,
                ATTR_CRYPTOCURRENCY_NAME: None,
                ATTR_CRYPTOCURRENCY_SYMBOL: None,
                ATTR_CURRENCY_NAME: self.currency_name,
                ATTR_MULTIPLIER: self.multiplier,
                ATTR_IMAGE: None,
            }
        return {
            ATTR_CRYPTOCURRENCY_ID: self.cryptocurrency_id,
            ATTR_CRYPTOCURRENCY_NAME: data.get("name"),
            ATTR_CRYPTOCURRENCY_SYMBOL: data.get("symbol"),
            ATTR_CURRENCY_NAME: self.currency_name,
            ATTR_MULTIPLIER: self.multiplier,
            ATTR_IMAGE: data.get("image"),
        }


class CryptoinfoDerivedSensor(CoordinatorEntity[CryptoDataCoordinator], SensorEntity):
    """A metric sensor derived from the price API record (market cap, changes, ...)."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    entity_description: CryptoSensorEntityDescription

    def __init__(
        self,
        coordinator: CryptoDataCoordinator,
        description: CryptoSensorEntityDescription,
        cryptocurrency_id: str,
        currency_name: str,
        unit_of_measurement: str,
        base_unique_id: str,
        id_name: str,
    ) -> None:
        """Initialize the derived sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.cryptocurrency_id = cryptocurrency_id
        self.currency_name = currency_name
        self._attr_translation_placeholders = {
            "cryptocurrency": cryptocurrency_id.capitalize(),
            "currency": currency_name.upper(),
        }
        self._attr_unique_id = f"{base_unique_id}_{description.key}"
        self._attr_native_unit_of_measurement = resolve_price_unit(description, unit_of_measurement)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"cryptoinfo_{id_name or 'default'}")},
            name=f"Cryptoinfo {id_name or 'Wallet'}",
            manufacturer="CoinGecko",
            model="Cryptocurrency Tracker",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(
            self.coordinator.last_update_success
            and self.coordinator.data
            and self.cryptocurrency_id in self.coordinator.data
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the derived metric value."""
        data = self.coordinator.data.get(self.cryptocurrency_id) if self.coordinator.data else None
        if not data:
            return None
        try:
            value = self.entity_description.value_fn(data)
        except (KeyError, TypeError, ValueError):
            return None
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
