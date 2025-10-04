import logging

DOMAIN = "cryptoinfo"

# Price sensor configuration
CONF_ID = "id"
CONF_CRYPTOCURRENCY_IDS = "cryptocurrency_ids"
CONF_CURRENCY_NAME = "currency_name"
CONF_MULTIPLIERS = "multipliers"
CONF_UPDATE_FREQUENCY = "update_frequency"
CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
CONF_MIN_TIME_BETWEEN_REQUESTS = "min_time_between_requests"

# Mining sensor configuration
CONF_SENSOR_TYPE = "sensor_type"
CONF_BTC_ADDRESS = "btc_address"
CONF_POOL_URL = "pool_url"
CONF_CKPOOL_REGION = "ckpool_region"

# CKPool regions
CKPOOL_REGION_GLOBAL = "solo.ckpool.org"
CKPOOL_REGION_EU = "eusolostats.ckpool.org"

# Sensor types
SENSOR_TYPE_PRICE = "price"
SENSOR_TYPE_BTC_NETWORK = "btc_network"
SENSOR_TYPE_BTC_MEMPOOL = "btc_mempool"
SENSOR_TYPE_CKPOOL_MINING = "ckpool_mining"

SENSOR_PREFIX = "Cryptoinfo "
ATTR_LAST_UPDATE = "last_update"
ATTR_CRYPTOCURRENCY_ID = "cryptocurrency_id"
ATTR_CRYPTOCURRENCY_NAME = "cryptocurrency_name"
ATTR_CRYPTOCURRENCY_SYMBOL = "cryptocurrency_symbol"
ATTR_CURRENCY_NAME = "currency_name"
ATTR_BASE_PRICE = "baseprice"
ATTR_MULTIPLIER = "multiplier"
ATTR_24H_VOLUME = "24h_volume"
ATTR_1H_CHANGE = "1h_change"
ATTR_24H_CHANGE = "24h_change"
ATTR_7D_CHANGE = "7d_change"
ATTR_14D_CHANGE = "14d_change"
ATTR_30D_CHANGE = "30d_change"
ATTR_1Y_CHANGE = "1y_change"
ATTR_MARKET_CAP = "market_cap"
ATTR_CIRCULATING_SUPPLY = "circulating_supply"
ATTR_TOTAL_SUPPLY = "total_supply"
ATTR_ATH = "ath"
ATTR_ATH_DATE = "ath_date"
ATTR_ATH_CHANGE = "ath_change"
ATTR_RANK = "rank"
ATTR_IMAGE = "image"

API_ENDPOINT = "https://api.coingecko.com/api/v3/"

_LOGGER = logging.getLogger(__name__)
