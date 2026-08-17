# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Price sensor metrics promoted from attributes to dedicated entities (market cap, 24h volume, 1h–1y changes, circulating/total supply, ATH, rank) — 13 per tracked coin.
- Mining metrics as dedicated entities: network (difficulty, block height, retarget, halving), mempool (size, fees), CKPool (hashrates, best share, workers, blocks).
- `sensor_descriptions.py` module: frozen + kw_only `EntityDescription` with `value_fn` (mandatory since HA 2025.1).
- 33 entity translation keys (EN + FR, vouvoiement) with `{cryptocurrency}` / `{currency}` placeholders.

### Changed

- Minimum Home Assistant bumped to `2025.11` (`hacs.json`) to unlock `UpdateFailed(retry_after=)` on CoinGecko rate limits.
- `const/const.py` flattened to `const.py`; `helper/` renamed to `api/`.
- `CryptoInfoOptionsFlow` extracted from `config_flow.py` into `options_flow.py`.
- `_LOGGER` no longer lives in `const` (module loggers everywhere) — anti-pattern removed.
- Price sensor `extra_state_attributes` reduced to identity only (id, name, symbol, currency, multiplier, image).

### Fixed

- Rate-limit backoff now honors CoinGecko `Retry-After` via `UpdateFailed(retry_after=)`.

### Removed

- Client-side share formatting (`_format_share`) — best share/ever exposed as raw numeric sensors.

## [1.8.3] - 2026-06-25

### Changed

- Internal refactor: deduplicated the price sensor `unique_id` into a shared helper used by both the sensor platform and the reconfigure flow, removed dead code (unused exceptions and constant), and hoisted inline imports. No behaviour change; `unique_id`s are unchanged.
- Updated development and CI tooling via Renovate (mypy 2.x, pre-commit-hooks v6, mirrors-mypy v2, softprops/action-gh-release v3, and other GitHub Actions / dev dependencies).

### Fixed

- Documentation: corrected the attribute names in the README — `baseprice` and `ath` (were wrongly documented as `base_price` and `ath_price`).

## [1.8.2] - 2026-01-24

### Fixed

- Sensor: Remove incompatible device_class monetary (was causing HA warnings with state_class measurement)

## [1.8.1] - 2026-01-23

### Fixed

- CI: Ignore PT001 in tests to avoid ruff auto-fix conflict
- CI: Use space-separated ignore list for HACS validation
- CI: Ignore HACS topics and issues checks
- HACS: Remove invalid keys from root hacs.json and duplicate file
- CI: Resolve pre-commit and mypy compatibility issues

### Changed

- Refactor: Upgrade to Home Assistant Quality Scale standards
  - Added circuit breaker and rate limiting patterns to API clients
  - Improved exception handling with typed exceptions
  - Added UTC-aware datetime usage
  - Enhanced resilience with retry logic and exponential backoff
