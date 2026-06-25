"""Pure helper functions for the Cryptoinfo integration.

Functions here must stay free of Home Assistant and I/O so they remain trivially
testable in isolation.
"""

from __future__ import annotations

from .const.const import SENSOR_PREFIX


def build_price_unique_id(id_name: str, cryptocurrency_id: str, currency_name: str) -> str:
    """Return the stable unique_id for a price sensor entity.

    Shared by the sensor platform and the reconfigure flow so the two can never
    drift apart. A drift would silently break orphaned-entity removal, since the
    flow computes this id to look entities up in the registry.
    """
    return f"{SENSOR_PREFIX}{id_name}_{cryptocurrency_id}_{currency_name}".lower().replace(" ", "_")
