# ARCHITECTURE.md

## Vue d'ensemble

Intégration Home Assistant `cryptoinfo` — capteurs de prix des cryptomonnaies via l'API CoinGecko, avec capteurs minage Bitcoin via Mempool.space et CKPool.

Minimum HA : 2025.11 · Python ≥ 3.13 · `config_flow` + `options_flow` + `reauth` + `reconfigure`.

## Flux de données

```
Config flow (config_flow.py) + Options flow (options_flow.py)
   → async_setup_entry (__init__.py)
   → entry.runtime_data = CryptoInfoRuntimeData (const.py)
      → coordinator.py (DataUpdateCoordinator, polling, retry_after sur rate limit)
         → api/coingecko_api.py (prix, retry + circuit breaker + rate limit)
         → api/blockchain_api.py (minage : Mempool.space + CKPool)
         → sensor.py / mining_sensor.py (plateformes)
            → sensor_descriptions.py (EntityDescription frozen+kw_only + value_fn)
```

## Modules

| Fichier | Rôle |
|---------|------|
| `__init__.py` | `async_setup_entry` / `async_unload_entry`, `runtime_data`, migration d'entrée |
| `config_flow.py` | ConfigFlow : user, price_search, select_crypto, configure, mining, reauth, reconfigure |
| `options_flow.py` | OptionsFlow : update_frequency, min_time_between_requests |
| `coordinator.py` | `CryptoDataCoordinator[dict]`, `UpdateFailed(retry_after=)` sur rate limit |
| `const.py` | Constantes `Final`, dataclasses (`CryptoInfoRuntimeData`), `CryptoInfoConfigEntry` |
| `sensor.py` | Plateforme sensor prix : `CryptoinfoSensor` (prix) + `CryptoinfoDerivedSensor` (13 métriques) |
| `sensor_descriptions.py` | `CryptoSensorEntityDescription` (frozen+kw_only) + listes prix/network/mempool/ckpool |
| `mining_sensor.py` | Coordinators BTC + entités minage (network, mempool, ckpool) |
| `api/coingecko_api.py` | Client CoinGecko (retry backoff, rate limit, circuit breaker) |
| `api/blockchain_api.py` | Client Mempool.space + CKPool (parsing JSON/HTML, conversion hashrate) |
| `api/crypto_info_data.py` | Données partagées entre entries (min_time_between_requests) |
| `api/storage_helper.py` | Persistance `Store` HA |
| `exceptions.py` | `CryptoInfoError` hiérarchie (Connection, RateLimit, InvalidResponse) |
| `helpers.py` | Fonctions pures (`build_price_unique_id`) |
| `diagnostics.py` | Export diagnostic HA (redaction adresses) |

## Entités

- **Prix** (par crypto suivie) : 1 sensor prix (unique_id stable `build_price_unique_id`) + 13 entités dérivées (`<base>_<metric_key>`) — market cap, volume, changes 1h→1y, supplies, ATH, rank.
- **Minage** : sensor principal (hashrate/mempool size) + entités dérivées par métrique (difficulty, block height, retarget, halving, fees, workers, blocks…).
- Toutes : `CoordinatorEntity`, `_attr_has_entity_name`, `translation_key` + placeholders, `PARALLEL_UPDATES = 0`.
- `unique_id` déterministes et stables ; les entités principales n'ont jamais changé de format.

## Ajouter une nouvelle métrique prix

1. Ajouter une `CryptoSensorEntityDescription` dans `PRICE_DESCRIPTIONS` (`sensor_descriptions.py`) avec `key`, `translation_key`, `value_fn`.
2. Ajouter la clé `entity.sensor.<translation_key>` dans `strings.json`, `translations/en.json` et `translations/fr.json` (placeholders `{cryptocurrency} {currency}`).
3. Le setup crée automatiquement l'entité dérivée pour chaque crypto (boucle sur `PRICE_DESCRIPTIONS`).

## Tests

Suite pytest sous `tests/` (104 tests) : API mockées (`AiohttpClientMocker`), config/options flow, coordinator, capteurs prix et minage, edge cases. Couverture 98.7 % (coordinator/API/sensor 100 %).
