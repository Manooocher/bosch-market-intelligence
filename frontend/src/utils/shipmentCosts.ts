import type { CostType } from '../api/shipments';

export const COST_TYPE_LABELS: Record<CostType, string> = {
  shipping: 'حمل',
  customs: 'گمرک',
  insurance: 'بیمه',
  warehouse: 'انبارداری',
  handling: 'هندلینگ',
  other: 'سایر',
};

export const COST_TYPES: CostType[] = ['shipping', 'customs', 'insurance', 'warehouse', 'handling', 'other']; 