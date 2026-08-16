# ARCHITECTURE.md

## Vue d'ensemble

Intégration Home Assistant `cryptoinfo` — capteurs de prix des cryptomonnaies via l'API CoinGecko, avec capteurs minage Bitcoin via Mempool.space.

## Flux de données

```
Config flow (config_flow.py)
   → async_setup_entry (__init__.py)
   → entry.runtime_data = CryptoInfoRuntimeData (const/const.py)
      → coordinator.py (DataUpdateCoordinator, polling périodique)
         → helper/coingecko_api.py (prix, API CoinGecko)
         → helper/blockchain_api.py (données minage, Mempool.space)
         → sensor.py (entités de prix)
         → mining_sensor.py (capteurs minage Bitcoin)
   → diagnostics.py (export diagnostic HA)
```

## Modules

| Fichier | Rôle |
|---------|------|
| `__init__.py` | `async_setup_entry` / `async_unload_entry`, `runtime_data`, migration d'entrée |
| `config_flow.py` | Flow UI + reconfigure, options (ajout/suppression de cryptos) |
| `coordinator.py` | `DataUpdateCoordinator` centralisant les pollings |
| `const/const.py` | Constantes, dataclasses (`CryptoInfoRuntimeData`), domain |
| `helper/coingecko_api.py` | Client CoinGecko (prix, mapping symboles) |
| `helper/blockchain_api.py` | Client Mempool.space (minage Bitcoin : difficulty, hashrate, halving) |
| `helper/crypto_info_data.py` | Structure des données prix |
| `helper/storage_helper.py` | Persistance locale (liste des cryptos suivies) |
| `exceptions.py` | Exceptions custom (`CryptoInfoConnectionError`) |
| `helpers.py` | Helpers génériques |
| `sensor.py` | Plateforme sensor des prix |
| `mining_sensor.py` | Capteurs minage Bitcoin |
| `diagnostics.py` | Diagnostic HA (debug facilité) |

## État de l'entrée

`runtime_data` (patterns modernes HA 2024+, pas de `hass.data[DOMAIN]`).

## Tests

Suite pytest sous `tests/` (102 tests) : API mockées (`AiohttpClientMocker`), config flow, coordonnateur, capteurs. Couverture cible ≥ 95 %.
