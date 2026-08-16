# Nabkade Market Intelligence — Frontend

React + TypeScript dashboard for Bosch market intelligence. It displays
market prices scraped from Torob (ترب) alongside Nabkade (نابکده) selling
prices and computes margin/competition analytics.

> Stack: React 18 · TypeScript · Vite · TanStack Query · TanStack Table ·
> Recharts · Tailwind CSS · axios

---

## Setup

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### Requirements

- **Backend running on `http://localhost:8000`** (the FastAPI app at the repo
  root). In dev, the Vite proxy forwards `/api/*` to `:8000` so there is **no
  CORS** to worry about. Start it with:

  ```bash
  cd <repo-root>
  source venv/bin/activate
  uvicorn api.main:app --host 0.0.0.0 --port 8000
  ```

## Environment variables

| File | Variable | Purpose |
|------|----------|---------|
| `.env.development` | `VITE_API_URL` | **Leave empty** — dev uses the Vite proxy (same-origin `/api`) to dodge CORS |
| `.env.production` | `VITE_API_URL` | Set to the backend origin, e.g. `http://SERVER_IP:8000` |

`src/api/client.ts` reads `import.meta.env.VITE_API_URL`:
empty → requests go to same-origin `/api` (proxied); set → direct to backend.

## Build & lint

```bash
npm run build   # tsc -b && vite build (strict TypeScript)
npm run lint    # eslint
```

`npm run preview` serves the production build locally.

## Directory layout

```
src/
  api/          # typed backend client + adapter layer
    client.ts     axios instance + error interceptor
    types.ts      Raw (backend) + mapped/UI interfaces
    mappers.ts    raw -> mapped transformations
    products.ts   /api/products endpoints
    margins.ts    /api/margins endpoints (paginated)
    market.ts     /api/market/overview + exchange-rate + health
  hooks/        # React Query hooks (useProducts, useProductDetail, useSellers, useMargins, useMarket)
  components/
    layout/       AppLayout, Sidebar (RTL), Header (exchange-rate + freshness)
    ui/           Card, Badge, Loading, ErrorState, EmptyState, Pagination
    products/     ProductTable, ProductRow, ProductSearch, CategoryFilter,
                  ProductDetailHeader, PriceComparisonCards
    sellers/      SellerTable, SellerRow
    charts/       PriceDistribution (Recharts)
  pages/        # MarketOverviewPage, ProductsPage, ProductDetailPage, MarginsPage
  utils/        # categories.ts, colors.ts, format.ts (fa-IR number formatting)
```

## Pages & routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | MarketOverviewPage | 4 stat cards, freshness banner, margin histogram |
| `/products` | ProductsPage | Product table: server-side sort/pagination, client-side search + category filter |
| `/products/:torobId` | ProductDetailPage | Detail header, price-comparison cards, seller table, price-distribution chart |
| `/margins` | MarginsPage | Margin-focused table with "فقط منفیها" toggle |
| `/_debug/data` | DataProbe | Temporary raw-data probe (development aid) |

## Caching strategy

Data updates only every few days, so React Query caches aggressively:

- `staleTime: 1 hour`
- `gcTime: 4 hours`
- `refetchOnWindowFocus: false`

## Currency note

Despite DB column names ending in `_rial`, **prices are stored and returned in
Toman** (10 Rial = 1 Toman, but the system does not divide). Margin fields
(`margin_vs_min_pct`, etc.) compare Nabkade price vs Torob market price; a
positive margin means Nabkade sells *above* market, negative means below.
`is_profitable = margin > 0`.

## Known limitations

- `search` and `category` filters on the Products page are applied **client-side
  to the current page**. The backend `/api/products` supports these params, but
  the page filters the fetched slice in-memory; with large datasets this only
  filters the loaded page. (The Vite/browser-cached page slice is 25 rows.)
- Margins "فقط منفیها" toggle is client-side over the loaded page.
- The margin histogram on the overview page reads up to 100 products.
- With full crawl data (7000+ products), pagination + server-side search/category
  should be used; the backend already supports `?search=&category=` for that.