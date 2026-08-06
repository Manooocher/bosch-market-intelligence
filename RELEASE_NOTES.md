# Release Notes — v1.0.0-rc1

**Release Date:** 2026-08-07  
**Status:** Release Candidate 1  
**Production Readiness:** READY FOR PRODUCTION

---

## Summary

This is the first release candidate of the Torob Intelligence Platform. The system is production-ready and capable of autonomous daily monitoring of ~450 Bosch products on Torob.com.

## What's Included

### Core Infrastructure
- Shared crawler with residential proxy support (Proxy-Cheap)
- Circuit breaker, retry policy, rate limiting
- TLS fingerprint impersonation via curl_cffi
- Structured error classification (18 categories)

### Product Matching
- SKU extraction with 149 Bosch prefixes
- Multi-signal scoring (SKU, category, brand, token overlap)
- Confidence classification (HIGH/MEDIUM/LOW)
- Watch List generation in SQLite

### Daily Monitor
- Processes ~500 products per run
- Fetches USDT/IRT exchange rate from Tabdeal
- Parses seller data from Torob
- Computes market statistics (min/max/avg/median prices, competition score)
- Stores results in SQLite

### Production Operations
- Startup validation (Python, databases, env, proxy)
- Execution locking (prevents concurrent runs)
- Automatic backup before each run
- Health checks at startup
- Graceful shutdown on SIGTERM/SIGINT
- Structured logging with rotating files

### Deployment
- Linux/cron wrapper scripts
- Systemd service configuration
- Environment variable configuration via .env

## Performance

| Metric | Value |
|--------|-------|
| Products per run | ~500 |
| Run duration | ~71 minutes |
| Success rate | ~83% |
| Products/minute | 7.4 |

## Known Limitations

1. Seller data limited to 1 seller per product (search API limitation)
2. Proxy stability varies with residential IP rotation
3. Some products fail due to Torob API timeouts

## Upgrade Notes

From v0.9.0:
1. Replace root-level Python files with `crawler/` and `matcher/` packages
2. Update `.env` with new environment variables
3. Run `python -m cli.bootstrap` to rebuild Watch List
4. Set up cron with `scripts/monitor.sh`
