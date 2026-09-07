# Frontend Architecture — Nabkade Market Intelligence Dashboard

This document describes the React frontend under `frontend/`. It is a companion
to `README.md` (project-level) and `API_CONTRACT.md` (backend contracts).

## Stack

- **React 18** + **TypeScript 5.5** (strict)
- **Vite 5** build tool (`tsc -b && vite build`)
- **Tailwind CSS 3** for styling (single `index.css`; no App.css)
- **TanStack** — React Query (server state), React Table (virtualized table),
  React Virtual (rendering)
- **Recharts** — price distribution charts
- **React Router 6** — navigation
- **lucide-react** — icons

## Component hierarchy

```
App (App.tsx)
├── ErrorBoundary                 ← global render-error fallback (RTL UI)
└── QueryClientProvider           ← TanStack React Query
    └── BrowserRouter / Routes
        └── AppLayout (per-route shell)
            ├── ToastProvider     ← global toast context + renderer
            ├── Sidebar           ← navigation
            ├── Header            ← exchange-rate chip, menu
            └── main → Outlet     ← rendered page
                ├── MarketOverviewPage
                ├── ProductsPage / ProductDetailPage
                ├── MarginsPage
                └── Shipments*Page (list / detail / form)
```

>`/_debug/data` (DataProbe) is dynamically imported and only mounted when
>`import.meta.env.DEV` is true. It is pruned entirely from production builds.

## State management

Two mechanisms are used, deliberately separated:

1. **Server state — TanStack React Query** (`src/hooks/*.ts`)
   - Read queries: `useProducts`, `useProductOverview`, `useProductDetail`,
     `useSellers`, `useCategories`, `useMargins`, `useMarket`, `useShipments`.
   - Write operations: `useMutation` (React Query) for create / update /
     delete / finalize. Success handlers call
     `queryClient.invalidateQueries({ queryKey: [...] })` to refresh reads.
   - Cache policy (long-lived market data): stale 1h, gc 4h for read queries;
     shipments use shorter staleness so list/detail stay responsive.

2. **Client state — React Context** (`components/ui/toastContext.ts`)
   - `ToastProvider` (mounted in `AppLayout`) exposes `ToastApi`
     (`success` / `error` / `info`) via `useToast()`. This keeps transient
     user-feedback (toasts) out of React Query and shared across pages.

Pages own local form state with `useState`/`useEffect` (e.g. shipment form).

## Error handling strategy

- **Render errors:** `ErrorBoundary` wraps the whole app. It uses
  `getDerivedStateFromError` to capture any render/lifecycle throw and renders
  a Persian, RTL fallback with **تلاش مجدد** (reset boundary) and
  **بارگذاری مجدد صفحه** (full reload). `componentDidCatch` logs to console.
- **Async / API errors:** every mutation uses `useMutation` with `onError`
  that surfaces a message through `apiErrorMessage(e, fallback)` and shows a
  red toast. The same helper normalizes the many axios/FastAPI error shapes.
- **Read errors:** pages render `ErrorState` (with a retry button) rather than
  throwing.

## File organization

```
frontend/src/
├── api/         thin axios wrappers + response mappers (Raw* → UI types)
├── components/  reusable UI (ui/), layout (layout/), feature components
│   └── ui/      Badge, Card, Empty/ErrorState, Loading, Toast(+Provider),
│                ToastContainer, toastContext
├── hooks/       React Query hooks per resource (useProducts, useToast, …)
├── pages/       one file per route; `_debug/` for dev-only diagnostics
└── utils/       pure helpers (format, date, colors, categories, error,
                 shipmentCosts)
```

Conventions:

- One focused commit per logical change (see git log).
- UI-facing text is Persian; numerals go through `formatPrice`/`formatNumber`
  (fa-IR grouping).
- Backend DTOs are never used directly; `api/mappers.ts` normalizes them into
  UI shapes.
- Layout/styling uses Tailwind utility classes throughout.