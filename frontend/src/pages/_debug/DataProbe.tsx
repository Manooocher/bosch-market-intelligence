import { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import type { AxiosError } from 'axios';

type FieldCheck = {
  name: string;
  ok: boolean;
  value: unknown;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

export function DataProbe() {
  const [raw, setRaw] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get('/api/products', { params: { page: 1, per_page: 3 } })
      .then((res: { data: Record<string, unknown> }) => {
        setRaw(res.data);
        setLoading(false);
      })
      .catch((err: AxiosError) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-6 font-mono text-sm">Loading...</div>;
  if (error) return <div className="p-6 text-red-600 font-mono">Error: {error}</div>;

  const products = raw?.products;
  const firstProduct = Array.isArray(products) && products.length > 0 ? (products[0] as Record<string, unknown>) : null;

  const fieldChecks: FieldCheck[] = !firstProduct
    ? []
    : [
        { name: 'category', ok: typeof firstProduct.category !== 'undefined' && firstProduct.category !== null, value: firstProduct.category },
        { name: 'torob_url', ok: typeof firstProduct.torob_url !== 'undefined' && firstProduct.torob_url !== null, value: firstProduct.torob_url },
        { name: 'margin_vs_min_pct', ok: 'margin_vs_min_pct' in firstProduct, value: firstProduct.margin_vs_min_pct },
        { name: 'margin_vs_median_pct', ok: 'margin_vs_median_pct' in firstProduct, value: firstProduct.margin_vs_median_pct },
        { name: 'margin_vs_min_rial', ok: 'margin_vs_min_rial' in firstProduct, value: firstProduct.margin_vs_min_rial },
        { name: 'margin_vs_median_rial', ok: 'margin_vs_median_rial' in firstProduct, value: firstProduct.margin_vs_median_rial },
        { name: 'seller_count', ok: 'seller_count' in firstProduct, value: firstProduct.seller_count },
        { name: 'competition_score', ok: 'competition_score' in firstProduct, value: firstProduct.competition_score },
        { name: 'sku', ok: 'sku' in firstProduct, value: firstProduct.sku },
        { name: 'nabkade_product_id', ok: 'nabkade_product_id' in firstProduct, value: firstProduct.nabkade_product_id },
      ];

  return (
    <div className="p-6 font-mono text-sm space-y-6" dir="ltr">
      <h1 className="text-xl font-bold">Data Probe — Raw API Response</h1>

      <div className="space-y-2">
        <h2 className="font-semibold">Pagination</h2>
        <pre className="bg-slate-900 text-green-400 p-4 rounded-lg overflow-x-auto">
          {JSON.stringify(isRecord(raw) ? raw.pagination : null, null, 2)}
        </pre>
      </div>

      <div className="space-y-2">
        <h2 className="font-semibold">Field Verification (first product)</h2>
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-slate-100">
              <th className="text-left p-2 border">Field</th>
              <th className="text-left p-2 border">Status</th>
              <th className="text-left p-2 border">Value</th>
            </tr>
          </thead>
          <tbody>
            {fieldChecks.map((f) => (
              <tr key={f.name} className={f.ok ? 'bg-emerald-50' : 'bg-red-50'}>
                <td className="p-2 border font-medium">{f.name}</td>
                <td className="p-2 border">
                  {f.ok ? (
                    <span className="text-emerald-600 font-bold">✓</span>
                  ) : (
                    <span className="text-red-600 font-bold">✗</span>
                  )}
                </td>
                <td className="p-2 border max-w-xs truncate">
                  {f.ok ? JSON.stringify(f.value) : 'MISSING'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-2">
        <h2 className="font-semibold">Raw First Product</h2>
        <pre className="bg-slate-900 text-green-400 p-4 rounded-lg overflow-x-auto text-xs">
          {JSON.stringify(firstProduct, null, 2)}
        </pre>
      </div>
    </div>
  );
}