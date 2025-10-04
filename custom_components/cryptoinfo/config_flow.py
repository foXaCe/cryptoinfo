#!/usr/bin/env python3
"""
Config flow component for Cryptoinfo
Author: Johnny Visser
"""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .helper.crypto_info_data import CryptoInfoData
from .helper.coingecko_api import CoinGeckoAPI

from .const.const import (
    _LOGGER,
    CONF_CRYPTOCURRENCY_IDS,
    CONF_CURRENCY_NAME,
    CONF_ID,
    CONF_MIN_TIME_BETWEEN_REQUESTS,
    CONF_MULTIPLIERS,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_UPDATE_FREQUENCY,
    DOMAIN,
)


class CryptoInfoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self._coin_list = []
        self._selected_cryptos = []
        self._config_data = {}

    async def _validate_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate the input."""
        errors = {}

        # Split and clean the values
        crypto_ids = [
            name.strip().lower() for name in user_input[CONF_CRYPTOCURRENCY_IDS].split(",")
        ]
        multipliers = [mult.strip() for mult in user_input[CONF_MULTIPLIERS].split(",")]

        # Check if the counts match
        if len(crypto_ids) != len(multipliers):
            return {
                "base": "mismatch_values",
                "count_context": {
                    "crypto_count": len(crypto_ids),
                    "multiplier_count": len(multipliers),
                },
            }

        # Validate cryptocurrency IDs against CoinGecko API
        api = CoinGeckoAPI(self.hass)
        validation_results = await api.validate_cryptocurrency_ids(crypto_ids)

        invalid_ids = [
            crypto_id for crypto_id, is_valid in validation_results.items()
            if not is_valid
        ]

        if invalid_ids:
            return {
                "base": "invalid_cryptocurrency_ids",
                "invalid_context": {
                    "invalid_ids": ", ".join(invalid_ids),
                },
            }

        return errors

    async def async_step_reconfigure(self, user_input: Mapping[str, Any] | None = None):
        """Handle reconfiguration flow - Step 1: Search or browse."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry

        # Store entry data for later use
        self._config_data["entry"] = entry

        # Initialize data if needed
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = CryptoInfoData(self.hass)
            await self.hass.data[DOMAIN].async_initialize()

        # Load coin list
        if not self._coin_list:
            api = CoinGeckoAPI(self.hass)
            self._coin_list = await api.get_coin_list()

        if user_input is not None:
            # Store search query if provided
            search_query = user_input.get("search_query", "").strip()
            self._config_data["search_query"] = search_query
            return await self.async_step_reconfigure_select()

        # Show search form
        search_schema = vol.Schema(
            {
                vol.Optional(
                    "search_query",
                    description={"suggested_value": ""},
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=search_schema,
            errors={},
            description_placeholders={
                "info": "Search for cryptocurrencies to add or modify. Leave empty to see top 10 by market cap."
            },
        )

    async def async_step_reconfigure_select(self, user_input: dict[str, Any] | None = None):
        """Handle crypto selection for reconfiguration - Step 2."""
        errors = {}
        entry = self._config_data["entry"]

        if user_input is not None:
            selected = user_input.get("selected_cryptos", [])
            if not selected:
                errors["base"] = "no_crypto_selected"
            else:
                self._selected_cryptos = selected
                return await self.async_step_reconfigure_configure()

        # Get existing cryptocurrencies
        existing_ids = [id.strip() for id in entry.data.get(CONF_CRYPTOCURRENCY_IDS, "").split(",")]

        # Filter coin list based on search query
        search_query = self._config_data.get("search_query", "").lower()

        if search_query:
            # Search mode: show search results + ALWAYS include existing cryptos
            search_results = [
                coin for coin in self._coin_list
                if search_query in coin["id"].lower()
                or search_query in coin["name"].lower()
                or search_query in coin["symbol"].lower()
            ][:100]

            # Merge search results with existing cryptos (avoid duplicates)
            seen = {coin["id"] for coin in search_results}
            filtered_coins = search_results.copy()

            # Add existing cryptos that aren't in search results
            for coin in self._coin_list:
                if coin["id"] in existing_ids and coin["id"] not in seen:
                    filtered_coins.append(coin)
                    seen.add(coin["id"])
        else:
            # Default mode: show top 10 by market cap + existing cryptos
            api = CoinGeckoAPI(self.hass)
            top_coins = await api.get_top_cryptocurrencies(limit=10)

            # Merge top 10 with existing cryptos (avoid duplicates)
            seen = {coin["id"] for coin in top_coins}
            filtered_coins = top_coins.copy()

            # Add existing cryptos that aren't in top 10
            for coin in self._coin_list:
                if coin["id"] in existing_ids and coin["id"] not in seen:
                    filtered_coins.append(coin)
                    seen.add(coin["id"])

        # Create options for selector
        crypto_options = {
            coin["id"]: f"{coin['name']} ({coin['symbol'].upper()})"
            for coin in filtered_coins
        }

        if not crypto_options:
            errors["base"] = "no_results"
            return await self.async_step_reconfigure()

        # Pre-select ONLY existing cryptocurrencies
        default_selected = [id for id in existing_ids if id in crypto_options]

        select_schema = vol.Schema(
            {
                vol.Required(
                    "selected_cryptos",
                    default=default_selected
                ): cv.multi_select(crypto_options),
            }
        )

        return self.async_show_form(
            step_id="reconfigure_select",
            data_schema=select_schema,
            errors=errors,
            description_placeholders={
                "info": f"Top 10 by market cap shown. Your {len(existing_ids)} current crypto(s) are pre-selected." if not search_query else f"Search results for '{search_query}'. Your current cryptos are also shown and pre-selected."
            },
        )

    async def async_step_reconfigure_configure(self, user_input: dict[str, Any] | None = None):
        """Handle configuration for reconfiguration - Step 3."""
        errors = {}
        entry = self._config_data["entry"]
        default_min_time = self.hass.data[DOMAIN].min_time_between_requests

        if user_input is not None:
            multipliers = user_input.get(CONF_MULTIPLIERS, "").strip()
            multipliers_list = [m.strip() for m in multipliers.split(",") if m.strip()]

            if len(multipliers_list) != len(self._selected_cryptos):
                errors["base"] = "mismatch_values"
                errors["count_context"] = {
                    "crypto_count": len(self._selected_cryptos),
                    "multiplier_count": len(multipliers_list),
                }
            else:
                # Build final config - preserve optional fields from existing entry if not provided
                final_config = {
                    CONF_ID: user_input.get(CONF_ID) or entry.data.get(CONF_ID, ""),
                    CONF_CRYPTOCURRENCY_IDS: ", ".join(self._selected_cryptos),
                    CONF_MULTIPLIERS: ", ".join(multipliers_list),
                    CONF_CURRENCY_NAME: user_input[CONF_CURRENCY_NAME],
                    CONF_UNIT_OF_MEASUREMENT: user_input.get(CONF_UNIT_OF_MEASUREMENT) or entry.data.get(CONF_UNIT_OF_MEASUREMENT, ""),
                    CONF_UPDATE_FREQUENCY: user_input[CONF_UPDATE_FREQUENCY],
                    CONF_MIN_TIME_BETWEEN_REQUESTS: user_input[CONF_MIN_TIME_BETWEEN_REQUESTS],
                }

                # Update shared data
                self.hass.data[DOMAIN].min_time_between_requests = final_config[
                    CONF_MIN_TIME_BETWEEN_REQUESTS
                ]

                # Update entry data
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=final_config,
                )

                # Remove orphaned entities (cryptos that were removed from selection)
                from homeassistant.helpers import entity_registry as er
                from .const.const import SENSOR_PREFIX
                entity_reg = er.async_get(self.hass)

                old_crypto_ids = [id.strip() for id in entry.data.get(CONF_CRYPTOCURRENCY_IDS, "").split(",")]
                removed_cryptos = [id for id in old_crypto_ids if id not in self._selected_cryptos]

                if removed_cryptos:
                    _LOGGER.debug(f"Removing entities for removed cryptos: {removed_cryptos}")
                    for crypto_id in removed_cryptos:
                        # Build unique_id for this crypto
                        unique_id = f"{SENSOR_PREFIX}{final_config[CONF_ID]}_{crypto_id}_{final_config[CONF_CURRENCY_NAME]}".lower().replace(" ", "_")
                        # Find entity by unique_id
                        for entity_id, entity_entry in entity_reg.entities.items():
                            if entity_entry.unique_id == unique_id:
                                entity_reg.async_remove(entity_id)
                                _LOGGER.debug(f"Removed entity {entity_id} with unique_id {unique_id}")
                                break

                # Reload the entry
                await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reconfigure_successful")

        # Get existing multipliers or create defaults
        existing_ids = [id.strip() for id in entry.data.get(CONF_CRYPTOCURRENCY_IDS, "").split(",")]
        existing_multipliers = [m.strip() for m in entry.data.get(CONF_MULTIPLIERS, "1").split(",")]

        # Build default multipliers for selected cryptos
        default_multipliers = []
        for crypto_id in self._selected_cryptos:
            if crypto_id in existing_ids:
                idx = existing_ids.index(crypto_id)
                default_multipliers.append(existing_multipliers[idx] if idx < len(existing_multipliers) else "1")
            else:
                default_multipliers.append("1")

        crypto_names = ", ".join(self._selected_cryptos)

        configure_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ID,
                    default=entry.data.get(CONF_ID, ""),
                ): str,
                vol.Required(
                    CONF_MULTIPLIERS,
                    default=", ".join(default_multipliers),
                ): str,
                vol.Required(
                    CONF_CURRENCY_NAME,
                    default=entry.data.get(CONF_CURRENCY_NAME, "usd"),
                ): str,
                vol.Optional(
                    CONF_UNIT_OF_MEASUREMENT,
                    default=entry.data.get(CONF_UNIT_OF_MEASUREMENT, ""),
                ): str,
                vol.Required(
                    CONF_UPDATE_FREQUENCY,
                    default=entry.data.get(CONF_UPDATE_FREQUENCY, 5),
                ): cv.positive_float,
                vol.Required(
                    CONF_MIN_TIME_BETWEEN_REQUESTS,
                    default=default_min_time,
                ): cv.positive_float,
            }
        )

        return self.async_show_form(
            step_id="reconfigure_configure",
            data_schema=configure_schema,
            errors=errors,
            description_placeholders={
                "selected_cryptos": crypto_names,
                **errors.get("count_context", {}),
            },
        )

    async def _redo_configuration(
        self,
        entry_data: Mapping[str, Any],
        errors: dict[str, Any] | None = None,
        count_context: dict[str, Any] | None = None,
    ):
        if errors is None:
            errors = {}
        if count_context is None:
            count_context = {}

        # Get value from shared data if available
        default_min_time = 0.25
        if DOMAIN in self.hass.data:
            default_min_time = self.hass.data[DOMAIN].min_time_between_requests

        cryptoinfo_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ID,
                    description={"suggested_value": entry_data.get(CONF_ID, "")},
                ): str,
                vol.Required(
                    CONF_CRYPTOCURRENCY_IDS,
                    default=entry_data[CONF_CRYPTOCURRENCY_IDS],
                ): str,
                vol.Required(
                    CONF_CURRENCY_NAME, default=entry_data[CONF_CURRENCY_NAME]
                ): str,
                vol.Required(
                    CONF_MULTIPLIERS, default=entry_data[CONF_MULTIPLIERS]
                ): str,
                vol.Optional(
                    CONF_UNIT_OF_MEASUREMENT,
                    description={
                        "suggested_value": entry_data.get(CONF_UNIT_OF_MEASUREMENT, "")
                    },
                ): str,
                vol.Required(
                    CONF_UPDATE_FREQUENCY, default=entry_data[CONF_UPDATE_FREQUENCY]
                ): cv.positive_float,
                vol.Required(
                    CONF_MIN_TIME_BETWEEN_REQUESTS,
                    description={"suggested_value": default_min_time},
                ): cv.positive_float,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=cryptoinfo_schema,
            errors=errors,
            description_placeholders={**count_context},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle a flow initialized by the user - Step 1: Choose sensor type."""
        from .const.const import (
            CONF_SENSOR_TYPE,
            SENSOR_TYPE_PRICE,
            SENSOR_TYPE_BTC_NETWORK,
            SENSOR_TYPE_BTC_MEMPOOL,
            SENSOR_TYPE_CKPOOL_MINING,
        )

        if user_input is not None:
            sensor_type = user_input.get(CONF_SENSOR_TYPE)
            self._config_data[CONF_SENSOR_TYPE] = sensor_type

            if sensor_type == SENSOR_TYPE_PRICE:
                return await self.async_step_price_search()
            elif sensor_type in [SENSOR_TYPE_BTC_NETWORK, SENSOR_TYPE_BTC_MEMPOOL, SENSOR_TYPE_CKPOOL_MINING]:
                return await self.async_step_mining_config()

        # Show sensor type selection
        sensor_type_schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_TYPE, default=SENSOR_TYPE_PRICE): vol.In({
                    SENSOR_TYPE_PRICE: "💰 Cryptocurrency Price Tracker",
                    SENSOR_TYPE_BTC_NETWORK: "⛓️ Bitcoin Network Stats",
                    SENSOR_TYPE_BTC_MEMPOOL: "📦 Bitcoin Mempool Stats",
                    SENSOR_TYPE_CKPOOL_MINING: "⛏️ CKPool Solo Mining Stats",
                }),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=sensor_type_schema,
            description_placeholders={
                "info": "Choose the type of sensor you want to create."
            },
        )

    async def async_step_price_search(self, user_input: dict[str, Any] | None = None):
        """Handle cryptocurrency price sensor - Step 2: Search or browse."""
        errors = {}

        # Initialize data if needed
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = CryptoInfoData(self.hass)
            await self.hass.data[DOMAIN].async_initialize()

        # Load coin list
        if not self._coin_list:
            api = CoinGeckoAPI(self.hass)
            self._coin_list = await api.get_coin_list()

        if user_input is not None:
            # Store search query if provided
            search_query = user_input.get("search_query", "").strip()
            self._config_data["search_query"] = search_query
            return await self.async_step_select_crypto()

        # Show search form
        search_schema = vol.Schema(
            {
                vol.Optional(
                    "search_query",
                    description={"suggested_value": ""},
                ): str,
            }
        )

        return self.async_show_form(
            step_id="price_search",
            data_schema=search_schema,
            errors=errors,
            description_placeholders={
                "info": "Search for cryptocurrencies by name, symbol, or ID. Leave empty to see top 10 by market cap."
            },
        )

    async def async_step_select_crypto(self, user_input: dict[str, Any] | None = None):
        """Handle crypto selection - Step 2: Select cryptocurrencies."""
        errors = {}

        if user_input is not None:
            selected = user_input.get("selected_cryptos", [])
            if not selected:
                errors["base"] = "no_crypto_selected"
            else:
                self._selected_cryptos = selected
                return await self.async_step_configure()

        # Filter coin list based on search query
        search_query = self._config_data.get("search_query", "").lower()

        if search_query:
            # Search mode: show search results
            filtered_coins = [
                coin for coin in self._coin_list
                if search_query in coin["id"].lower()
                or search_query in coin["name"].lower()
                or search_query in coin["symbol"].lower()
            ][:100]  # Limit to 100 results
        else:
            # Default mode: show top 10 by market cap
            api = CoinGeckoAPI(self.hass)
            filtered_coins = await api.get_top_cryptocurrencies(limit=10)

        # Create options for selector
        crypto_options = {
            coin["id"]: f"{coin['name']} ({coin['symbol'].upper()})"
            for coin in filtered_coins
        }

        if not crypto_options:
            errors["base"] = "no_results"
            return await self.async_step_price_search()

        select_schema = vol.Schema(
            {
                vol.Required("selected_cryptos"): cv.multi_select(crypto_options),
            }
        )

        return self.async_show_form(
            step_id="select_crypto",
            data_schema=select_schema,
            errors=errors,
            description_placeholders={
                "info": "Top 10 by market cap shown by default. Use search to find others." if not search_query else f"Search results for '{search_query}'"
            },
        )

    async def async_step_configure(self, user_input: dict[str, Any] | None = None):
        """Handle configuration - Step 3: Configure multipliers and settings."""
        errors = {}

        default_min_time = self.hass.data[DOMAIN].min_time_between_requests

        if user_input is not None:
            # Build cryptocurrency_ids and multipliers strings
            multipliers = user_input.get(CONF_MULTIPLIERS, "").strip()
            multipliers_list = [m.strip() for m in multipliers.split(",") if m.strip()]

            if len(multipliers_list) != len(self._selected_cryptos):
                errors["base"] = "mismatch_values"
                errors["count_context"] = {
                    "crypto_count": len(self._selected_cryptos),
                    "multiplier_count": len(multipliers_list),
                }
            else:
                # Build final config
                final_config = {
                    CONF_ID: user_input.get(CONF_ID, ""),
                    CONF_CRYPTOCURRENCY_IDS: ", ".join(self._selected_cryptos),
                    CONF_MULTIPLIERS: ", ".join(multipliers_list),
                    CONF_CURRENCY_NAME: user_input[CONF_CURRENCY_NAME],
                    CONF_UNIT_OF_MEASUREMENT: user_input.get(CONF_UNIT_OF_MEASUREMENT, ""),
                    CONF_UPDATE_FREQUENCY: user_input[CONF_UPDATE_FREQUENCY],
                    CONF_MIN_TIME_BETWEEN_REQUESTS: user_input[CONF_MIN_TIME_BETWEEN_REQUESTS],
                }

                try:
                    await self.async_set_unique_id(final_config[CONF_ID])
                    self._abort_if_unique_id_configured()

                    # Update shared data
                    self.hass.data[DOMAIN].min_time_between_requests = final_config[
                        CONF_MIN_TIME_BETWEEN_REQUESTS
                    ]

                    return self.async_create_entry(
                        title=f"Cryptoinfo - {final_config[CONF_ID] or 'Wallet'}",
                        data=final_config,
                    )
                except Exception as ex:
                    _LOGGER.error(f"Error creating entry: {ex}")
                    errors["base"] = f"Error creating entry: {ex}"

        # Generate default multipliers (1 for each selected crypto)
        default_multipliers = ", ".join(["1"] * len(self._selected_cryptos))

        # Create description of selected cryptos
        crypto_names = ", ".join(self._selected_cryptos)

        configure_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ID,
                    description={"suggested_value": "My Wallet"},
                ): str,
                vol.Required(
                    CONF_MULTIPLIERS,
                    default=default_multipliers,
                ): str,
                vol.Required(
                    CONF_CURRENCY_NAME,
                    default="usd",
                ): str,
                vol.Optional(
                    CONF_UNIT_OF_MEASUREMENT,
                    description={"suggested_value": "$"},
                ): str,
                vol.Required(
                    CONF_UPDATE_FREQUENCY,
                    default=5,
                ): cv.positive_float,
                vol.Required(
                    CONF_MIN_TIME_BETWEEN_REQUESTS,
                    default=default_min_time,
                ): cv.positive_float,
            }
        )

        return self.async_show_form(
            step_id="configure",
            data_schema=configure_schema,
            errors=errors,
            description_placeholders={
                "selected_cryptos": crypto_names,
                **errors.get("count_context", {}),
            },
        )

    async def async_step_mining_config(self, user_input: dict[str, Any] | None = None):
        """Handle mining sensor configuration."""
        from .const.const import (
            CONF_BTC_ADDRESS,
            CONF_SENSOR_TYPE,
            SENSOR_TYPE_BTC_NETWORK,
            SENSOR_TYPE_BTC_MEMPOOL,
            SENSOR_TYPE_CKPOOL_MINING,
        )

        errors = {}
        sensor_type = self._config_data.get(CONF_SENSOR_TYPE)

        if user_input is not None:
            final_config = {
                CONF_SENSOR_TYPE: sensor_type,
                CONF_ID: user_input.get(CONF_ID, ""),
                CONF_UPDATE_FREQUENCY: user_input.get(CONF_UPDATE_FREQUENCY, 5),
            }

            # Add BTC address if CKPool sensor
            if sensor_type == SENSOR_TYPE_CKPOOL_MINING:
                btc_address = user_input.get(CONF_BTC_ADDRESS, "").strip()
                if not btc_address:
                    errors["base"] = "btc_address_required"
                else:
                    final_config[CONF_BTC_ADDRESS] = btc_address

            if not errors:
                try:
                    # Use sensor type + ID as unique ID
                    unique_id = f"{sensor_type}_{final_config[CONF_ID]}".lower().replace(" ", "_")
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    sensor_names = {
                        SENSOR_TYPE_BTC_NETWORK: "Bitcoin Network",
                        SENSOR_TYPE_BTC_MEMPOOL: "Bitcoin Mempool",
                        SENSOR_TYPE_CKPOOL_MINING: "CKPool Mining",
                    }

                    return self.async_create_entry(
                        title=f"{sensor_names.get(sensor_type, 'Mining')} - {final_config[CONF_ID] or 'Stats'}",
                        data=final_config,
                    )
                except Exception as ex:
                    _LOGGER.error(f"Error creating mining sensor: {ex}")
                    errors["base"] = f"Error creating entry: {ex}"

        # Build schema based on sensor type
        if sensor_type == SENSOR_TYPE_CKPOOL_MINING:
            mining_schema = vol.Schema(
                {
                    vol.Optional(CONF_ID, description={"suggested_value": "My Mining"}): str,
                    vol.Required(CONF_BTC_ADDRESS): str,
                    vol.Required(CONF_UPDATE_FREQUENCY, default=5): cv.positive_float,
                }
            )
            description = "Configure CKPool solo mining sensor. Enter your Bitcoin address used for mining."
        else:
            mining_schema = vol.Schema(
                {
                    vol.Optional(CONF_ID, description={"suggested_value": "BTC"}): str,
                    vol.Required(CONF_UPDATE_FREQUENCY, default=5): cv.positive_float,
                }
            )
            description = f"Configure {sensor_type.replace('_', ' ').title()} sensor."

        return self.async_show_form(
            step_id="mining_config",
            data_schema=mining_schema,
            errors=errors,
            description_placeholders={"info": description},
        )
