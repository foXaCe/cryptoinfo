"""Entity descriptions for Cryptoinfo sensors.

Frozen + kw_only is mandatory for EntityDescription subclasses since HA 2025.1.
Each description carries a ``value_fn`` mapping a raw API record to the sensor
state, so the platform files stay free of business logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntityDescription,
    SensorStateClass,
)

# Price sensor unit marker: the currency symbol configured by the user.
UNIT_PRICE = "price_unit"


@dataclass(frozen=True, kw_only=True)
class CryptoSensorEntityDescription(SensorEntityDescription):
    """Description for a Cryptoinfo sensor with a value extractor."""

    value_fn: Callable[[dict[str, Any]], Any] = lambda data: None


PRICE_DESCRIPTIONS: tuple[CryptoSensorEntityDescription, ...] = (
    CryptoSensorEntityDescription(
        key="market_cap",
        translation_key="crypto_market_cap",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UNIT_PRICE,
        value_fn=lambda data: data.get("market_cap"),
    ),
    CryptoSensorEntityDescription(
        key="volume_24h",
        translation_key="crypto_volume_24h",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UNIT_PRICE,
        value_fn=lambda data: data.get("total_volume"),
    ),
    CryptoSensorEntityDescription(
        key="change_1h",
        translation_key="crypto_change_1h",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("price_change_percentage_1h_in_currency"),
    ),
    CryptoSensorEntityDescription(
        key="change_24h",
        translation_key="crypto_change_24h",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("price_change_percentage_24h_in_currency"),
    ),
    CryptoSensorEntityDescription(
        key="change_7d",
        translation_key="crypto_change_7d",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("price_change_percentage_7d_in_currency"),
    ),
    CryptoSensorEntityDescription(
        key="change_14d",
        translation_key="crypto_change_14d",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("price_change_percentage_14d_in_currency"),
    ),
    CryptoSensorEntityDescription(
        key="change_30d",
        translation_key="crypto_change_30d",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("price_change_percentage_30d_in_currency"),
    ),
    CryptoSensorEntityDescription(
        key="change_1y",
        translation_key="crypto_change_1y",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("price_change_percentage_1y_in_currency"),
    ),
    CryptoSensorEntityDescription(
        key="circulating_supply",
        translation_key="crypto_circulating_supply",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("circulating_supply"),
    ),
    CryptoSensorEntityDescription(
        key="total_supply",
        translation_key="crypto_total_supply",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("total_supply"),
    ),
    CryptoSensorEntityDescription(
        key="ath",
        translation_key="crypto_ath",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UNIT_PRICE,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("ath"),
    ),
    CryptoSensorEntityDescription(
        key="ath_change",
        translation_key="crypto_ath_change",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("ath_change_percentage"),
    ),
    CryptoSensorEntityDescription(
        key="rank",
        translation_key="crypto_rank",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("market_cap_rank"),
    ),
)

MINING_NETWORK_DESCRIPTIONS: tuple[CryptoSensorEntityDescription, ...] = (
    CryptoSensorEntityDescription(
        key="difficulty",
        translation_key="network_difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("difficulty"),
    ),
    CryptoSensorEntityDescription(
        key="block_height",
        translation_key="network_block_height",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("block_height"),
    ),
    CryptoSensorEntityDescription(
        key="next_difficulty_block",
        translation_key="network_next_difficulty_block",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("next_difficulty_block"),
    ),
    CryptoSensorEntityDescription(
        key="blocks_until_retarget",
        translation_key="network_blocks_until_retarget",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("blocks_until_retarget"),
    ),
    CryptoSensorEntityDescription(
        key="difficulty_change",
        translation_key="network_difficulty_change",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("difficulty_change"),
    ),
    CryptoSensorEntityDescription(
        key="next_halving_block",
        translation_key="network_next_halving_block",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("next_halving_block"),
    ),
    CryptoSensorEntityDescription(
        key="blocks_until_halving",
        translation_key="network_blocks_until_halving",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("blocks_until_halving"),
    ),
)

MINING_MEMPOOL_DESCRIPTIONS: tuple[CryptoSensorEntityDescription, ...] = (
    CryptoSensorEntityDescription(
        key="mempool_mb",
        translation_key="mempool_mb",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="MB",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("mempool_bytes"),
    ),
    CryptoSensorEntityDescription(
        key="fee_fastest",
        translation_key="mempool_fee_fastest",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="sat/vB",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("fee_fastest"),
    ),
    CryptoSensorEntityDescription(
        key="fee_half_hour",
        translation_key="mempool_fee_half_hour",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="sat/vB",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("fee_half_hour"),
    ),
    CryptoSensorEntityDescription(
        key="fee_hour",
        translation_key="mempool_fee_hour",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="sat/vB",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("fee_hour"),
    ),
    CryptoSensorEntityDescription(
        key="fee_economy",
        translation_key="mempool_fee_economy",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="sat/vB",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("fee_economy"),
    ),
    CryptoSensorEntityDescription(
        key="fee_minimum",
        translation_key="mempool_fee_minimum",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="sat/vB",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("fee_minimum"),
    ),
)

CKPOOL_DESCRIPTIONS: tuple[CryptoSensorEntityDescription, ...] = (
    CryptoSensorEntityDescription(
        key="hashrate_1h",
        translation_key="ckpool_hashrate_1h",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="GH/s",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("hashrate_1h"),
    ),
    CryptoSensorEntityDescription(
        key="hashrate_24h",
        translation_key="ckpool_hashrate_24h",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="GH/s",
        suggested_display_precision=2,
        value_fn=lambda data: data.get("hashrate_24h"),
    ),
    CryptoSensorEntityDescription(
        key="best_share",
        translation_key="ckpool_best_share",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("best_share"),
    ),
    CryptoSensorEntityDescription(
        key="best_ever",
        translation_key="ckpool_best_ever",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("best_ever"),
    ),
    CryptoSensorEntityDescription(
        key="workers",
        translation_key="ckpool_workers",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("workers"),
    ),
    CryptoSensorEntityDescription(
        key="blocks_found",
        translation_key="ckpool_blocks_found",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("blocks_found"),
    ),
)


def resolve_price_unit(description: CryptoSensorEntityDescription, unit: str) -> str | None:
    """Return the real unit string, replacing the UNIT_PRICE marker when needed."""
    if description.native_unit_of_measurement == UNIT_PRICE:
        return unit or None
    return description.native_unit_of_measurement
