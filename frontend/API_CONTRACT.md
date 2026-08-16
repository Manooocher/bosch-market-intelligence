# API Contract — Nabkade Market Intelligence

Documentation of every backend endpoint the frontend consumes, with verified
response shapes. Backend: FastAPI (`api/main.py`) on port **8000**.
In development the Vite proxy forwards `/api/*` to `http://localhost:8000`; in
production the client uses `VITE_API_URL`.

**Headers (client sends):**
- `Accept: application/json`

**Error shape (FastAPI):** unhandled errors return
`{"detail": "<message>"}` (client logs it via an axios interceptor).

**HTTP methods allowed by backend CORS:** `GET` only.

---

## 1. `GET /api/products`

List products with server-side pagination, sorting, search, and category filter.

**Query params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `page` | int | `1` | 1-based |
| `per_page` | int | `20` | max 100 |
| `sort_by` | string | `competition_score` | column name on `LatestPrice` |
| `sort_dir` | `asc`/`desc` | `desc` | |
| `search` | string | — | case-insensitive `ilike` on `title` + `sku` |
| `category` | string | — | exact match on `category` column (e.g. `washing_machine`, `refrigerator`) |

**Response:**

```json
{
  "pagination": { "page": 1, "per_page": 20, "total": 2, "total_pages": 1 },
  "products": [ "ProductItem" ]
}
```

**`ProductItem`:**

```json
{
  "nabkade_product_id": "TEST-WASHER-1",
  "torob_product_id": "759291d9-d194-4fdf-a868-5a9976402eb9",
  "sku": "WAT24460IR",
  "title": "ماشین لباسشویی بوش ...",
  "category": "washing_machine",
  "torob_url": "https://torob.com/p/759291d9-d194-4fdf-a868-5a9976402eb9",
  "last_fetched_at": "2026-08-11 15:14:47+00:00",
  "seller_count": 1,
  "min_price_rial": 139344000,
  "max_price_rial": 139344000,
  "avg_price_rial": 139344000,
  "median_price_rial": 139344000,
  "min_price_usd": 744518,
  "max_price_usd": 744518,
  "avg_price_usd": 744518,
  "median_price_usd": 744518,
  "competition_score": 37,
  "margin_vs_min_pct": -54.8,
  "margin_vs_min_rial": -49344000,
  "margin_vs_median_pct": -54.8,
  "margin_vs_median_rial": -49344000,
  "updated_at": "2026-08-11 15:14:47+00:00"
}
```

> **Units:** despite the `_rial` names, `*_price_rial` / `margin_*_rial` values
> are **Toman**. `min_price_rial = 139344000` is the real Torob price in Toman.
> Margin = Nabkade − market. Negative ⇒ we sell below market.

---

## 2. `GET /api/products/{torob_id}`

Product detail. **Response = `ProductItem` plus:**

```json
{
  "market_stats": {
    "seller_count": 1,
    "min_price_rial": 139344000,
    "max_price_rial": 139344000,
    "avg_price_rial": 139344000,
    "median_price_rial": 139344000,
    "competition_score": 37,
    "fetched_at": "2026-08-11 15:14:47+00:00",
    "freshness": "fresh" | "acceptable" | "stale" | "unknown"
  },
  "price_distribution": {
    "buckets": [
      { "range": "139M-139M", "count": 1 },
      { "range": "139M-139M", "count": 0 }
    ]
  }
}
```

- 4 buckets computed server-side from seller prices.
- Not found → `{"error": "Product not found", "torob_product_id": "<id>"}`.

---

## 3. `GET /api/products/{torob_id}/sellers`

List sellers for a product, sorted by `price_rial` ascending.

**Response:**

```json
{
  "torob_product_id": "759291d9-...",
  "sellers": [
    {
      "seller_id": "75823",
      "seller_name": "آرکانا هوم",
      "price_rial": 139344000,
      "seller_score": 5,
      "seller_city": "تهران",
      "is_in_stock": true,
      "is_promoted": false
    }
  ]
}
```

**Mapping (adapter):** `seller_city → shop_city`, `seller_score → shop_score`,
`is_promoted → is_advertisement`.

---

## 4. `GET /api/margins`

Margin analytics with server-side pagination + sorting. Margins are computed in
Python across the full dataset, sorted, then sliced.

**Query params:** `page`, `per_page` (≤100), `sort_by`
(one of `margin_vs_min_pct`, `margin_vs_median_pct`, `margin_vs_min_toman`,
`margin_vs_median_toman`, `nabkade_price_toman`, `market_min_price_toman`),
`sort_dir`.

**Response:**

```json
{
  "pagination": { "page": 1, "per_page": 20, "total": 2, "total_pages": 1 },
  "margins": [
    {
      "sku": "WAT24460IR",
      "torob_product_id": "759291d9-...",
      "title": "ماشین لباسشویی بوش ...",
      "category": "washing_machine",
      "torob_url": "https://torob.com/p/759291d9-...",
      "nabkade_price_toman": 90000000,
      "market_min_price_toman": 139344000,
      "market_median_price_toman": 139344000,
      "margin_vs_min_toman": -49344000,
      "margin_vs_median_toman": -49344000,
      "margin_vs_min_pct": -54.8,
      "margin_vs_median_pct": -54.8,
      "is_profitable": false
    }
  ]
}
```

> `is_profitable = margin_vs_min > 0`. Here `false` because Nabkade (90,000,000)
> is below the Torob market min (139,344,000).

---

## 5. `GET /api/market/overview`

Global market statistics + exchange rate.

**Response:**

```json
{
  "total_products": 2,
  "products_with_sellers": 2,
  "avg_sellers_per_product": 1.0,
  "avg_competition_score": 37.0,
  "usd_irt_rate": 0,
  "usd_irt_source": "tabdeal",
  "usd_irt_updated_at": "2026-08-14T21:15:23Z",
  "last_monitor_run": {
    "started_at": "...",
    "finished_at": "...",
    "products_succeeded": 2,
    "products_failed": 0,
    "status": "completed"
  }
}
```

- The exchange rate is exposed **here** only (no dedicated `/api/exchange-rate`
  endpoint); the frontend derives `ExchangeRate` from this payload.
- `last_monitor_run` may be `null` if no run has occurred.
- Note: `usd_irt_rate` is currently hardcoded/stale at `0` in the backend; the
  header shows the value as-is.

---

## 6. `GET /api/system/health`

**Response:**

```json
{
  "status": "healthy",
  "database": { "connected": true },
  "monitor": {
    "last_run_finished_at": "...",
    "last_run_status": "completed",
    "seconds_since_last_run": 279511
  },
  "timestamp": "2026-08-14T20:54:10Z"
}
```

`monitor` may be `{}` if no run has occurred.

---

## Frontend adapter layer

Raw shapes (`Raw*` in `src/api/types.ts`) map to UI shapes in
`src/api/mappers.ts`:

| Mapped | Derivation |
|--------|-----------|
| `ProductListItem.category` | `raw.category ?? 'دستهبندی نشده'` |
| `ProductListItem.torob_url` | `raw.torob_url ?? ''` (already built by backend) |
| `ProductListItem.freshness_hours` | hours since `last_fetched_at` |
| `ProductListItem.is_profitable` | `raw.margin_vs_min_rial != null && > 0` |
| `Seller.is_advertisement` | `raw.is_promoted` |
| `ProductDetail` | `mapProductItem(detail) + market_stats + price_distribution + sellers` |

## Verified discrepancies

| Endpoint | Spec assumption | Reality |
|----------|-----------------|---------|
| Health | `GET /api/health` | `GET /api/system/health` |
| Exchange rate | dedicated endpoint | embedded in `/api/market/overview` |
| Market categories | `GET /api/market/categories` | **does not exist** — Categories page dropdown is derived from fetched products + `CATEGORY_GROUPS` map |
| Margins | `/api/products/{id}/margin` | via `/api/margins` + fields in product list/detail |
| Seller fields | `shop_score`, `is_advertisement`, `warranty_info` | backend returns `seller_score`, `is_promoted`, no warranty |
| Units | rial | **Toman stored in `_rial` columns** — fixed in the bugfix sprint |

> **Known live-data caveats (test dataset):** the DB currently holds only the 2
> seeded products. `seller_snapshot` has 2 rows total.