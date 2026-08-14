// Categories are now served by the backend via /api/products?category=...
// The normalized_category values from the backend are English keys.
// This file maps them to display groups for the UI.

export type CategoryGroup = 'Cooking' | 'Cooling' | 'Washing' | 'Small' | 'Parts' | 'Other';

export interface CategoryInfo {
  group: CategoryGroup;
  label: string;
}

/** Maps backend normalized_category values to display groups and labels. */
export const CATEGORY_GROUPS: Record<string, CategoryInfo> = {
  // Cooking
  'cooker': { group: 'Cooking', label: 'اجاق گاز' },
  'cooking_oven': { group: 'Cooking', label: 'فر' },
  'built_in_oven': { group: 'Cooking', label: 'فر توکار' },
  'hood': { group: 'Cooking', label: 'هود آشپزخانه' },
  'microwave': { group: 'Cooking', label: 'مایکروویو' },
  'solar_oven': { group: 'Cooking', label: 'اجاق خورشیدی' },

  // Cooling
  'refrigerator': { group: 'Cooling', label: 'یخچال' },
  'freezer': { group: 'Cooling', label: 'فریزر' },
  'side_by_side': { group: 'Cooling', label: 'ساید بای ساید' },
  'twin': { group: 'Cooling', label: 'دوقلو' },
  'top_bottom': { group: 'Cooling', label: 'بالاپایین' },

  // Washing
  'washing_machine': { group: 'Washing', label: 'ماشین لباسشویی' },
  'dishwasher': { group: 'Washing', label: 'ماشین ظرفشویی' },
  'dryer': { group: 'Washing', label: 'خشک‌کن' },
  'steam_cleaner': { group: 'Washing', label: 'بخارشوی' },

  // Small Appliances
  'vacuum_cleaner': { group: 'Small', label: 'جاروبرقی' },
  'cordless_vacuum': { group: 'Small', label: 'جاروشارژی' },
  'iron': { group: 'Small', label: 'اتو بخار' },
  'kettle': { group: 'Small', label: 'کتری برقی' },
  'coffee_maker': { group: 'Small', label: 'قهوه‌ساز' },
  'espresso_machine': { group: 'Small', label: 'اسپرسوساز' },
  'juicer': { group: 'Small', label: 'آبمیوه‌گیری' },
  'blender': { group: 'Small', label: 'مخلوط‌کن' },
  'food_processor': { group: 'Small', label: 'غذاساز' },
  'toaster': { group: 'Small', label: 'تست و نان تست' },
  'meat_grinder': { group: 'Small', label: 'چرخ گوشت' },
  'hair_dryer': { group: 'Small', label: 'سشوار' },
  'hair_styler': { group: 'Small', label: 'حالت‌دهنده مو' },

  // Spare Parts
  'spare_parts_vacuum': { group: 'Parts', label: 'لوازم یدکی جارو' },
};

export function getCategoryGroup(category: string | null | undefined): CategoryGroup {
  if (!category) return 'Other';
  return CATEGORY_GROUPS[category]?.group ?? 'Other';
}

export function getCategoryLabel(category: string | null | undefined): string {
  if (!category) return 'دسته‌بندی نشده';
  return CATEGORY_GROUPS[category]?.label ?? category;
}

export function getCategoryLabelFromKey(category: string | null): string {
  return getCategoryLabel(category);
}