import { useMemo } from 'react';
import { CATEGORY_GROUPS, getCategoryLabel, CategoryGroup } from '../../utils/categories';

interface CategoryFilterProps {
  categories: string[]; // unique category keys available in the data
  value: string;        // selected key or '' for "all"
  onChange: (category: string) => void;
}

const GROUPS: CategoryGroup[] = ['Cooking', 'Cooling', 'Washing', 'Small', 'Parts', 'Other'];

const GROUP_LABELS: Record<CategoryGroup, string> = {
  Cooking: 'آشپزخانه',
  Cooling: 'سرمایشی',
  Washing: 'شستشو',
  Small: 'لوازم کوچک',
  Parts: 'لوازم یدکی',
  Other: 'سایر',
};

/** Grouped category dropdown derived from the categories present in the data. */
export function CategoryFilter({ categories, value, onChange }: CategoryFilterProps) {
  const grouped = useMemo(() => {
    const map = new Map<CategoryGroup, string[]>();
    GROUPS.forEach((g) => map.set(g, []));
    categories.forEach((cat) => {
      const group = CATEGORY_GROUPS[cat]?.group ?? 'Other';
      map.get(group)?.push(cat);
    });
    // Drop empty groups
    return Array.from(map.entries()).filter(([, cats]) => cats.length > 0);
  }, [categories]);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full sm:w-56 px-3 py-2.5 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      <option value="">همه دسته‌ها</option>
      {grouped.map(([group, cats]) => (
        <optgroup key={group} label={GROUP_LABELS[group]}>
          {cats.map((cat) => (
            <option key={cat} value={cat}>
              {getCategoryLabel(cat)}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}