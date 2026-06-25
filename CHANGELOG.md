# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
