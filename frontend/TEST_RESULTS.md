# Test Results — Nabkade Market Intelligence (Frontend)

Status of verification across all phases of the frontend build, including the
final bugfix sprint. Verified live against the FastAPI backend (port 8000) with
the Vite dev proxy (port 5173).

---

## 1. Automated checks

| Check | Command | Result |
|-------|---------|--------|
| TypeScript + production build | `npm run build` (`tsc -b && vite build`) | ✅ PASS (strict, no type errors) |
| ESLint (all `src/`) | `npx eslint src/` | ✅ PASS (exit 0, no errors) |
| Backend unit tests | `python -m pytest tests/ -v` | ✅ PASS (14 passed) |
| Backend API live probe (curl via proxy) | `/api/products`, `/sellers`, `/margins`, `/market/overview`, `/system/health`, search + category | ✅ PASS |

**Build output (final):**
```
✓ 2490 modules transformed
index.html 0.60 kB │ gzip 0.38 kB
CSS 16.62 kB │ gzip 3.88 kB
JS 723 kB │ gzip 214 kB
```
> Note: JS bundle is large because Recharts (~723 kB). Not blocking; flagged as a
> performance item under §4. A build-time chunk-size warning is emitted.

---

## 2. Manual UI checklist

| # | Check | Result |
|---|-------|--------|
| 1 | Sidebar renders on the RIGHT (RTL), title = **"Market Intelligence"** (not "Torob Intelligence") | ✅ |
| 2 | Header shows exchange rate from `/api/market/overview.usd_irt_rate` | ✅ (shows 0, per backend data) |
| 3 | Navigation links render with active state (نمای کلی بازار / محصولات / حاشیه سود) | ✅ |
| 4 | `/products` table shows product rows, formatted fa-IR prices, margin badges | ✅ |
| 5 | `/products` row click navigates to `/products/:torobId` | ✅ |
| 6 | Product detail: title, SKU/category/seller-count/freshness badges | ✅ |
| 7 | Product detail shows **"مشاهده در ترب"** (correct spelling) | ✅ |
| 8 | Product detail seller table: rank, seller name, city, price, score stars, stock | ✅ |
| 9 | Price-distribution Recharts bar chart renders | ✅ |
| 10 | WAT24460IR margin shows **negative** (−54.8%, red badge) — not +84.5% | ✅ |
| 11 | `/margins` table renders with margin columns + status badge | ✅ |
| 12 | "فقط منفیها" toggle filters rows | ✅ |
| 13 | No console errors on page load / navigation | ✅ (no 500s; see §4) |
| 14 | RTL throughout; Persian (fa-IR) number formatting | ✅ |

---

## 3. Bugfix sprint verification

### Bug 1 — `// 10` division removed
Live API (verified after fix):

```
WAT24460IR:
  nabkade_price_toman     = 90,000,000
  market_min_price_toman  = 139,344,000   (was 13,934,400 ✔ fixed)
  margin_vs_min_toman     = -49,344,000   (was +76,065,600 ✔ fixed)
  margin_vs_min_pct       = -54.8%        (was +84.5% ✔ fixed)
  is_profitable           = false         (was true ✔ fixed)

KSV36VIEP:
  margin_vs_min_pct       = -55.3%,  is_profitable = false
```

### Bug 2 & 3 — spelling + branding
- Zero occurrences of `نبکاده`, `توروب`, or `Torob Intelligence` in `src/` + `index.html` (verified by grep).
- `dist/` still contains stale branded strings but is gitignored and regenerated on the next `npm run build`.

### Bug 4 — 2-Seller investigation (report only; no fix)
```
Unique sellers: 2 | seller_snapshot rows: 2 | market_snapshot rows: 2
Products with sellers: 2 | Total products: 2
Seller count distribution: 1 seller → 2 products
```
Conclusion: sample-size/storage — the DB holds only the 2 seeded products, each
with 1 seller. No crawler defect discernible from this dataset.
> The prompt's diagnostic SQL referenced `seller_snapshot.torob_product_id`,
> which does **not** exist; corrected to join via `market_snapshot_id`.

---

## 4. Performance & console notes

- **Console errors:** none during normal navigation against the live backend.
- **Bundle size:** 723 kB JS due to Recharts. Recommended, if it matters:
  code-split the detail page (which imports Recharts) with `React.lazy()` /
  `manualChunks`. Not done — intentionally left as a known, non-blocking item.
- **Missing backend endpoints discovered:**
  - `GET /api/market/categories` — does not exist; the CategoryFilter is fed from
    the current page's product categories + the `CATEGORY_GROUPS` map.
  - Dedicated `/api/exchange-rate` — does not exist; derived from
    `/api/market/overview`.
- **Currency unit caveat:** prices are stored/returned in **Toman** although the
  DB columns are named `_rial`. Documented in API_CONTRACT.md and README.md.

---

## 5. How to run the checks yourself

```bash
# Backend (repo root)
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # strict tsc + vite build
npx eslint src/
```

Open `http://localhost:5173` and walk the manual checklist in §2. The temporary
raw-data probe lives at `/_debug/data`.