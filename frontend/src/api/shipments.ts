import { apiClient } from './client';

// ── Input types (matching backend ShipmentCreate / ShipmentItemCreate / ShipmentCostCreate) ──
export type CostType = 'shipping' | 'customs' | 'insurance' | 'warehouse' | 'handling' | 'other';

export interface ShipmentItemInput {
  title: string;
  sku?: string | null;
  quantity: number;
  unit_purchase_price_usd: number;
  nabkade_product_id?: string | null;
  torob_product_id?: string | null;
}

export interface ShipmentCostInput {
  cost_type: CostType;
  description?: string | null;
  amount_usd: number;
}

export interface ShipmentCreateInput {
  name: string;
  notes?: string | null;
  items: ShipmentItemInput[];
  costs: ShipmentCostInput[];
}

export interface ShipmentUpdateInput {
  name?: string;
  notes?: string | null;
  items?: ShipmentItemInput[];
  costs?: ShipmentCostInput[];
}

// ── Output types (matching ItemResultOut / ShipmentCostOut / ShipmentListRow / ShipmentDetailOut) ──
export interface ShipmentListItem {
  id: number;
  name: string;
  status: 'draft' | 'finalized';
  created_at: string | null;
  finalized_at: string | null;
  item_count: number;
  total_value_usd: number;
  total_costs_usd: number;
}

export interface ShipmentItemResult {
  id: number;
  title: string;
  sku: string | null;
  nabkade_product_id: string | null;
  torob_product_id: string | null;
  quantity: number;
  unit_purchase_price_usd: number;
  total_value_usd: number;
  allocated_cost_usd: number;
  allocated_cost_per_unit_usd: number;
  landed_cost_usd: number;
  landed_cost_per_unit_toman: number | null;
  market_min_toman: number | null;
  market_median_toman: number | null;
  margin_vs_min_toman: number | null;
  margin_vs_min_pct: number | null;
  margin_vs_median_toman: number | null;
  margin_vs_median_pct: number | null;
  is_profitable: boolean | null;
}

export interface ShipmentCostResult {
  id: number;
  cost_type: CostType;
  description: string | null;
  amount_usd: number;
}

export interface ShipmentDetail {
  id: number;
  name: string;
  status: 'draft' | 'finalized';
  notes: string | null;
  dollar_rate: number | null;
  created_at: string | null;
  finalized_at: string | null;
  total_value_usd: number;
  total_costs_usd: number;
  items: ShipmentItemResult[];
  costs: ShipmentCostResult[];
  message?: string | null;
}

export const shipmentsApi = {
  list: async (): Promise<ShipmentListItem[]> => {
    const res = await apiClient.get<ShipmentListItem[]>('/api/shipments');
    return res.data;
  },

  get: async (id: number): Promise<ShipmentDetail> => {
    const res = await apiClient.get<ShipmentDetail>(`/api/shipments/${id}`);
    return res.data;
  },

  create: async (payload: ShipmentCreateInput): Promise<ShipmentDetail> => {
    const res = await apiClient.post<ShipmentDetail>('/api/shipments', payload);
    return res.data;
  },

  update: async (id: number, payload: ShipmentUpdateInput): Promise<ShipmentDetail> => {
    const res = await apiClient.put<ShipmentDetail>(`/api/shipments/${id}`, payload);
    return res.data;
  },

  delete: async (id: number): Promise<{ status: string; id: number }> => {
    const res = await apiClient.delete<{ status: string; id: number }>(`/api/shipments/${id}`);
    return res.data;
  },

  finalize: async (id: number): Promise<ShipmentDetail> => {
    const res = await apiClient.post<ShipmentDetail>(`/api/shipments/${id}/finalize`);
    return res.data;
  },
};