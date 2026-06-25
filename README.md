## Home Assistant sensor component for cryptocurrencies

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
[![CI][ci-shield]][ci]
[![hassfest][hassfest-shield]][hassfest]
[![Maintenance][maintenance-shield]][maintenance]
[![Project Maintenance][maintainer-shield]][maintainer]

![icon_mini](https://github.com/user-attachments/assets/328f93d8-6ea7-4877-bc31-1c5b33c4583a)
### Powered by CoinGecko API

#### Provides Home Assistant sensors for all cryptocurrencies supported by CoinGecko

## Breaking changes for upgrading from v0.x.x to v1.x.x
If you've just updated from v0.x.x to v1.x.x please remove the cryptoinfo sensor from your configuration.yaml and follow [Installation step 2](#installation-step-2)

If you need more advanced features than this project offers, see [Cryptoinfo Advanced](https://github.com/TheHolyRoger/hass-cryptoinfo)

### Installation step 1:
There are 2 ways to install cryptoinfo:
1. Download 'cryptoinfo' from the HACS store
2. Copy the files in the /custom_components/cryptoinfo/ folder to: [homeassistant]/config/custom_components/cryptoinfo/

### Installation step 2
The next step is to add cryptoinfo sensors to your Home Assistant:
1. Browse to your Home Assistant config page
2. Press Settings --> Devices & Services

![image](https://github.com/user-attachments/assets/c4812206-835e-4239-9757-8645ae6c772b)

3. Press 'Add Integration' and search for 'cryptoinfo' and select the 'cryptoinfo' integration

![image](https://github.com/user-attachments/assets/83e3e165-61fa-4aa9-8421-9fc019bfae82)

4. Fill in the 'add new sensor' form

![image](https://github.com/user-attachments/assets/d76156df-dc2c-4f5f-bbdf-ea58570c5963)

### Properties
<pre>
- Identifier                                Unique name for the sensor
- Cryptocurrency id's                       One or more of the 'id' values (separated by a , character) that you can find on this <a href='https://api.coingecko.com/api/v3/coins/list' target='_blank'>page</a>
- Multipliers                               The number of coins/tokens (separated by a , character). The number of Multipliers must match the number of Cryptocurrency id's
- Currency name                             One of the currency names that you can find on this <a href='https://api.coingecko.com/api/v3/simple/supported_vs_currencies' target='_blank'>page</a>
- Unit of measurement                       You can use a currency symbol or you can make it empty. You can find some symbols on this <a href='https://en.wikipedia.org/wiki/Currency_symbol#List_of_currency_symbols_currently_in_use' target='_blank'>page</a>
- Update frequency (minutes)                How often should the value be refreshed? Beware of the <a href='https://support.coingecko.com/hc/en-us/articles/4538771776153-What-is-the-rate-limit-for-CoinGecko-API-public-plan' target='_blank'>CoinGecko rate limit</a> when using multiple sensors
- Minimum time between requests (minutes)   The minimum time between the other sensors and this sensor to make a data request to the API. (This property is shared and the same for every sensor). You can set this value to 0 if you only use 1 sensor
</pre>

### Attributes
The entities have some important attributes:
```
- last_update           This will return the date and time of the last update
- cryptocurrency_id     This will return the cryptocurrency id
- cryptocurrency_name   This will return the cryptocurrency name
- cryptocurrency_symbol This will return the cryptocurrency symbol
- currency_name         This will return the currency name
- baseprice             This will return the price of 1 coin / token in 'currency_name'(default = "usd") of the 'cryptocurrency_id'
- multiplier            This will return the number of coins / tokens
- 24h_volume            This will return the 24 hour volume in 'currency_name'(default = "usd") of the 'cryptocurrency_id'(default = "bitcoin")
- 1h_change             This will return the 1 hour change in percentage of the 'cryptocurrency_id'(default = "bitcoin")
- 24h_change            This will return the 24 hour change in percentage of the 'cryptocurrency_id'(default = "bitcoin")
- 7d_change             This will return the 7 day change in percentage of the 'cryptocurrency_id'(default = "bitcoin")
- 14d_change            This will return the 14 day change in percentage of the 'cryptocurrency_id'(default = "bitcoin")
- 30d_change            This will return the 30 day change in percentage of the 'cryptocurrency_id'(default = "bitcoin")
- 1y_change             This will return the 1 year change in percentage of the 'cryptocurrency_id'(default = "bitcoin")
- market_cap            This will return the total market cap of the 'cryptocurrency_id'(default = "bitcoin") displayed in 'currency_name'(default = "usd")
- circulating_supply    This will return the circulating supply of the 'cryptocurrency_id'(default = "bitcoin")
- total_supply          This will return the total supply of the 'cryptocurrency_id'(default = "bitcoin")
- ath                   This will return the All Time High Price of the 'currency_name'(default = "usd") of the 'cryptocurrency_id'(default = "bitcoin")
- ath_date              This will return the date when the All Time High was reached of the 'currency_name'(default = "usd") of the 'cryptocurrency_id'(default = "bitcoin")
- ath_change            This will return the percentage change from the All Time High of the 'currency_name'(default = "usd") of the 'cryptocurrency_id'(default = "bitcoin")
- rank                  This will return the cryptocurrency rank
- image                 This will return the cryptocurrency image
```

Template example for usage of attributes.
This example creates a new sensor with the attribute value '24h_volume' of the sensor 'sensor.cryptoinfo_main_wallet_ethereum_eur':
```yaml
  - platform: template
    sensors:
      cryptoinfo_main_wallet_ethereum_eur_24h_volume:
        value_template: "{{ state_attr('sensor.cryptoinfo_main_wallet_ethereum_eur', '24h_volume') | float(0) | round(0) }}"
        unit_of_measurement: "€"
```

If you want to know the total value of your cryptocurrencies, you could use this template as an example.
This example combines the total value of all your sensors into this 1 template sensor:
```yaml
  - platform: template
    sensors:
      crypto_total:
        value_template: >
          {{ integration_entities('cryptoinfo')
              | map('states')
              | map('float', 0)
              | sum | round(2) }}
        unit_of_measurement: >
          {{ expand(integration_entities('cryptoinfo'))
              | map(attribute='attributes.unit_of_measurement')
              | list | default(['$'], true)
              | first }}
        friendly_name: Total value of all my cryptocurrencies
```

### Mining sensors (Bitcoin)
Besides cryptocurrency prices, Cryptoinfo can also create Bitcoin mining-related sensors. Pick the sensor type on the first step of the configuration flow:

- **Bitcoin Network** — global network hashrate (EH/s), difficulty, block height, next difficulty retarget and next halving. Data from [mempool.space](https://mempool.space).
- **Bitcoin Mempool** — number of unconfirmed transactions, mempool size (MB) and recommended fees (sat/vB). Data from [mempool.space](https://mempool.space).
- **CKPool Solo Mining** — your solo mining statistics (hashrate 1h/24h, best share, workers) for a given Bitcoin address, on the EU or Global [CKPool](https://solo.ckpool.org). Requires your Bitcoin payout address.

### How data is updated
This integration is `cloud_polling`: a coordinator periodically requests the relevant public API (CoinGecko for prices, mempool.space / CKPool for mining) at the **Update frequency** you configured. All price sensors share a single, rate-limited client (retry with exponential backoff + circuit breaker) so they stay within CoinGecko's public limits. Increase **Update frequency** and **Minimum time between requests** if you run many price sensors.

### Configuration options
After a sensor is created you can adjust its **Update frequency** (and, for price sensors, the shared **Minimum time between requests**) without recreating it: Settings → Devices & Services → Cryptoinfo → the sensor → **Configure**. You can also use **Reconfigure** to change the tracked cryptocurrencies.

### Removal
To remove the integration: Settings → Devices & Services → **Cryptoinfo**, open the overflow menu (⋮) of the entry you want to remove and choose **Delete**. Repeat for each Cryptoinfo entry. The entities and devices are removed automatically. If you installed via HACS and want to remove the code as well, remove **Cryptoinfo** from HACS afterwards and restart Home Assistant.

### Known limitations
- CoinGecko's public API is rate limited (≈5–15 calls/min). With many price sensors, set a higher update frequency to avoid throttling.
- The CKPool EU pool exposes stats as an HTML page; parsing may break if the pool changes its frontend. The Global pool exposes a stable JSON API.
- `blocks_found` is not exposed by the CKPool JSON API and is always reported as `0`.
- Prices come from CoinGecko only; no other source is supported.

### Troubleshooting
- **Sensor shows `unavailable`** — the API call failed (rate limit, network, or maintenance). Sensors recover automatically on the next successful update. Check Settings → System → Logs for `custom_components.cryptoinfo` messages.
- **"Invalid cryptocurrency IDs"** in the config flow — use the exact `id` from the [CoinGecko coins list](https://api.coingecko.com/api/v3/coins/list) (e.g. `bitcoin`, not `BTC`).
- **Rate limited** — increase the **Update frequency** / **Minimum time between requests**, or reduce the number of price sensors.
- **Diagnostics** — download diagnostics from the integration entry (overflow menu) to share sanitized state when opening an issue (your Bitcoin address is redacted).

### Issues and new functionality
If there are any problems, please create an issue in https://github.com/foXaCe/cryptoinfo/issues
If you want new functionality added, please create an issue with a description of the new functionality that you want in: https://github.com/foXaCe/cryptoinfo/issues

## Credits

This integration is a maintained fork of [heyajohnny/cryptoinfo](https://github.com/heyajohnny/cryptoinfo) by [@heyajohnny](https://github.com/heyajohnny). Powered by the [CoinGecko API](https://www.coingecko.com/en/api).

<!-- Badges -->
[releases-shield]: https://img.shields.io/github/v/release/foXaCe/cryptoinfo?style=for-the-badge
[releases]: https://github.com/foXaCe/cryptoinfo/releases
[license-shield]: https://img.shields.io/github/license/foXaCe/cryptoinfo?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[ci-shield]: https://img.shields.io/github/actions/workflow/status/foXaCe/cryptoinfo/ci.yml?branch=main&style=for-the-badge&label=CI
[ci]: https://github.com/foXaCe/cryptoinfo/actions/workflows/ci.yml
[hassfest-shield]: https://img.shields.io/github/actions/workflow/status/foXaCe/cryptoinfo/hassfest.yml?branch=main&style=for-the-badge&label=hassfest
[hassfest]: https://github.com/foXaCe/cryptoinfo/actions/workflows/hassfest.yml
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg?style=for-the-badge
[maintenance]: https://github.com/foXaCe/cryptoinfo
[maintainer-shield]: https://img.shields.io/badge/maintainer-%40foXaCe-blue.svg?style=for-the-badge
[maintainer]: https://github.com/foXaCe
