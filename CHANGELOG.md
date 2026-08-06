# Changelog

All notable changes to the Torob Intelligence Platform are documented here.

## [v1.0.0-rc1] - 2026-08-07

### Added

- **Shared Crawler Infrastructure** (`crawler/` package)
  - HttpClient with curl_cffi TLS impersonation
  - ProxyManager with Proxy-Cheap residential proxy support
  - FingerprintManager for browser identity rotation
  - CircuitBreaker for failure prevention
  - RetryPolicy with 18 error categories
  - RequestScheduler with configurable batching
  - MetricsCollector for runtime statistics
  - TorobCrawler adapter for Torob API
  - Currency fetcher for USDT/IRT exchange rate
  - SellerParser for Torob product data
  - Statistics engine for market analysis
  - MonitorDB for SQLite persistence
  - Production utilities (startup validation, locking, backup, health checks)

- **Product Matcher** (`matcher/` package)
  - SKU extraction with 149 Bosch prefixes
  - Multi-signal scoring engine
  - Confidence classification (HIGH/MEDIUM/LOW)
  - SQLite-based Watch List storage
  - QA report generation

- **CLI Entry Points** (`cli/` package)
  - `python -m cli.bootstrap` — Catalog Recovery
  - `python -m cli.monitor` — Daily Monitor

- **Deployment Scripts** (`scripts/`)
  - `monitor.sh` — Linux/cron wrapper
  - `bootstrap.sh` — Linux/cron wrapper

- **Configuration**
  - `.env` support via python-dotenv
  - Proxy-Cheap residential proxy integration
  - Tabdeal exchange rate API

### Changed

- Optimized monitor rate profile (1-2s delays, batch=50)
- Added startup validation to CLI entry points
- Added execution locking to prevent concurrent runs
- Added automatic backup before monitor runs
- Added health checks at startup
- Added graceful shutdown on SIGTERM/SIGINT

### Fixed

- Monitor batch success counter (was always reporting 0)
- Monitor crash handling (runs now marked as interrupted)
- Proxy URL format for Proxy-Cheap gateway
- Currency fetcher response parsing

## [v0.9.0] - 2026-08-04

### Added

- Product Matcher with SKU extraction
- Watch List generation
- Catalog Recovery pipeline
- Proxy-Cheap residential proxy support
- Tabdeal exchange rate integration

### Changed

- Migrated from hardcoded prefix list to prefix dictionary
- Improved seller parsing with fallback logic

## [v0.8.0] - 2026-07-30

### Added

- Initial Torob catalog (~7000 Bosch products)
- Nabkade product catalog (435 products)
- Product matching infrastructure
- SQLite database schema

### Changed

- Migrated from direct HTTP requests to shared crawler
