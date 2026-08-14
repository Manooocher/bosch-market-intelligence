export function getMarginColor(pct: number | null): string {
  if (pct === null) return 'bg-slate-100 text-slate-600';
  if (pct > 10) return 'bg-emerald-100 text-emerald-700';
  if (pct >= 0) return 'bg-amber-100 text-amber-700';
  return 'bg-red-100 text-red-700';
}

export function getCompetitionColor(score: number | null): string {
  if (score === null) return 'bg-slate-100 text-slate-600';
  if (score < 33) return 'bg-emerald-100 text-emerald-700';  // Low competition
  if (score <= 66) return 'bg-amber-100 text-amber-700';      // Moderate
  return 'bg-red-100 text-red-700';                            // High competition
}

export function getFreshnessColor(hours: number | null): string {
  if (hours === null) return 'bg-slate-400';
  if (hours < 24) return 'bg-emerald-500';
  if (hours <= 96) return 'bg-amber-500';
  return 'bg-red-500';
}

export function getStockColor(inStock: boolean): string {
  return inStock ? 'text-emerald-600' : 'text-red-500';
}

export function getPromotedColor(isPromoted: boolean): string {
  return isPromoted ? 'bg-amber-100 text-amber-700' : 'text-slate-400';
}