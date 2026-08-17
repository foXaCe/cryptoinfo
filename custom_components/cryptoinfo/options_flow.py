"""Options flow for Cryptoinfo integration."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    CONF_MIN_TIME_BETWEEN_REQUESTS,
    CONF_SENSOR_TYPE,
    CONF_UPDATE_FREQUENCY,
    SENSOR_TYPE_PRICE,
)


class CryptoInfoOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Cryptoinfo."""

    VERSION = 1

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        entry = self.config_entry
        sensor_type = entry.data.get(CONF_SENSOR_TYPE, SENSOR_TYPE_PRICE)

        if user_input is not None:
            # Update options
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_update_freq = entry.data.get(CONF_UPDATE_FREQUENCY, 5)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_FREQUENCY,
                    default=entry.options.get(CONF_UPDATE_FREQUENCY, current_update_freq),
                ): cv.positive_float,
            }
        )

        # Add min_time option only for price sensors
        if sensor_type == SENSOR_TYPE_PRICE:
            current_min_time = entry.data.get(CONF_MIN_TIME_BETWEEN_REQUESTS, 0.25)
            options_schema = options_schema.extend(
                {
                    vol.Required(
                        CONF_MIN_TIME_BETWEEN_REQUESTS,
                        default=entry.options.get(CONF_MIN_TIME_BETWEEN_REQUESTS, current_min_time),
                    ): cv.positive_float,
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={"info": "Configure update intervals for this sensor."},
        )
