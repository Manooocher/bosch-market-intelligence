# Torob Intelligence Platform

A production-grade market intelligence system that monitors Bosch appliance prices on Torob.com, Iran's leading price comparison platform.

## Overview

The Torob Intelligence Platform automatically tracks market prices for ~450 Bosch home appliances on Torob.com and compares them against Nabkade's purchase prices to provide pricing intelligence and profit margin calculations.

**Key Features:**
- Automated daily price monitoring via residential proxy
- Real-time USDT/IRT exchange rate conversion
- Market statistics (min/max/avg/median prices, seller count, competition score)
- Product matching between Nabkade and Torob catalogs
- Catalog recovery for missing Bosch models
- Production-grade error handling and recovery
- SQLite persistence with backup strategy

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Entry Points                      │
├──────────────────┬──────────────────┬───────────────────┤
│  cli/bootstrap.py│  cli/monitor.py  │  matcher/main.py  │
│  (Recovery)      │  (Daily Monitor) │  (Product Match)  │
└────────┬─────────┴────────┬─────────┴─────────┬─────────┘
         │                  │                   │
         ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│              crawler/ (Shared Infrastructure)            │
│  HttpClient │ ProxyManager │ RetryPolicy │ CircuitBreaker│
│  Fingerprint│ Scheduler    │ Metrics     │ TorobCrawler  │
│  Currency   │ SellerParser │ Statistics  │ MonitorDB     │
│  Production │ Bootstrap    │ Recovery    │               │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│  watch_list.db │ monitor_store.db │ bosch_prefixes.json │
└─────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# Clone repository
git clone https://github.com/Manooocher/bosch-market-intelligence.git
cd torob-int

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TOROB_PROXY_ENABLED` | Enable residential proxy | Yes |
| `TOROB_PROXY_USER` | Proxy-Cheap username | Yes |
| `TOROB_PROXY_PASS` | Proxy-Cheap password | Yes |
| `TOROB_PROXY_COUNTRY` | Proxy country code (IR) | Yes |
| `TABDEAL_API_URL` | Exchange rate API endpoint | Yes |

### .env Example

```bash
TOROB_PROXY_ENABLED=true
TOROB_PROXY_USER=your_username
TOROB_PROXY_PASS=your_password_country-IR
TOROB_PROXY_COUNTRY=IR
TABDEAL_API_URL=https://api1.tabdeal.org/r/api/v1/depth?symbol=USDTIRT&limit=1
```

## Quick Start

### 1. Bootstrap (Recovery)

Recover missing Bosch models and build the Watch List:

```bash
python -m cli.bootstrap
```

### 2. Daily Monitor

Run the daily price monitoring:

```bash
python -m cli.monitor
```

### 3. Product Matcher

Rebuild the Watch List from catalogs:

```bash
python -m matcher.main
```

## Recovery Pipeline

```
Missing SKUs → Torob Search → Validate → Patch Catalog → Rebuild Matcher → Watch List
```

The recovery pipeline:
1. Loads missing SKUs from `data/analysis/catalog_coverage.csv`
2. Searches Torob for each SKU via residential proxy
3. Validates results (SKU in title, Bosch brand, no duplicates)
4. Patches `bosch_products_links.final.csv` with recovered products
5. Rebuilds matcher indexes and Watch List

## Matcher Pipeline

```
Torob Catalog + Nabkade Catalog → SKU Extraction → Candidate Generation → Scoring → Confidence → Watch List
```

The matcher:
1. Extracts Bosch model numbers (149 prefixes)
2. Generates candidates via inverted index
3. Scores candidates using multi-signal matching
4. Classifies confidence (HIGH/MEDIUM/LOW)
5. Builds Watch List in SQLite

## Daily Monitor

```
Watch List → Exchange Rate → Torob Search → Seller Parse → Statistics → SQLite
```

The monitor:
1. Loads ~500 products from Watch List (HIGH + MEDIUM confidence)
2. Fetches current USDT/IRT exchange rate from Tabdeal
3. Searches Torob for each product via residential proxy
4. Parses seller data and computes market statistics
5. Stores results in SQLite

## Project Structure

```
torob-int/
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── LICENSE                   # License
├── CHANGELOG.md             # Version history
├── RELEASE_NOTES.md          # Release notes
│
├── crawler/                  # Shared infrastructure
│   ├── config.py            # Configuration
│   ├── interfaces.py        # Abstract base classes
│   ├── http_client.py       # HTTP client
│   ├── proxy.py             # Proxy management
│   ├── proxy_health.py      # Proxy health tracking
│   ├── fingerprint.py       # Browser identity
│   ├── circuit_breaker.py   # Circuit breaker
│   ├── retry.py             # Error classification
│   ├── scheduler.py         # Request scheduling
│   ├── metrics.py           # Metrics collection
│   ├── torob.py             # Torob API adapter
│   ├── currency.py          # Exchange rate
│   ├── seller_parser.py     # Seller data parsing
│   ├── statistics.py        # Market statistics
│   ├── monitor.py           # Daily monitor
│   ├── monitor_db.py        # Monitor database
│   ├── bootstrap.py         # Catalog bootstrap
│   ├── recovery.py          # Catalog recovery
│   ├── discovery.py         # Category discovery
│   └── production.py        # Production utilities
│
├── matcher/                 # Product matching
│   ├── main.py             # Matcher entry point
│   ├── normalize.py        # Text normalization
│   ├── sku.py              # SKU extraction
│   ├── index.py            # Inverted index
│   ├── candidate.py        # Candidate generation
│   ├── scorer.py           # Scoring engine
│   ├── confidence.py       # Confidence classification
│   ├── store.py            # SQLite storage
│   ├── qa.py               # QA report
│   └── review.py           # Review queue
│
├── cli/                     # CLI entry points
│   ├── bootstrap.py       # Recovery pipeline
│   └── monitor.py         # Daily monitor
│
├── scripts/                # Deployment scripts
│   ├── bootstrap.sh       # Linux wrapper
│   └── monitor.sh         # Linux wrapper
│
├── tests/                  # Test suite
│   └── test_monitor_modules.py
│
└── data/                   # Data directory
    ├── bosch_prefixes.json    # SKU prefix dictionary
    ├── bosch_products_links.csv
    ├── bosch_products_links.final.csv
    ├── leaf_categories.json
    └── torob.sqlite3          # Original Torob data
```

## Production Deployment

### Linux (Recommended)

```bash
# Install
cd /opt/torob
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
vim .env

# Set up cron (daily at 6 AM)
chmod +x scripts/monitor.sh
crontab -e
# Add: 0 6 * * * /opt/torob/scripts/monitor.sh
```

### Systemd Service

```ini
[Unit]
Description=Torob Bosch Product Watcher
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/torob
ExecStart=/opt/torob/venv/bin/python -m cli.monitor
Restart=on-failure
RestartSec=300

[Install]
WantedBy=multi-user.target
```

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run matcher
python -m matcher.main

# Run monitor
python -m cli.monitor

# Run bootstrap
python -m cli.bootstrap
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
