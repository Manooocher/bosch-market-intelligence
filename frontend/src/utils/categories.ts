// Bosch category mapping + normalization helpers.

export const BOSCH_CATEGORIES = {
  // Cooking
  'اجاق گاز': { group: 'Cooking', label: 'اجاق گاز' },
  'فر برقی و گازی': { group: 'Cooking', label: 'فر' },
  'هود آشپزخانه': { group: 'Cooking', label: 'هود' },

  // Cooling
  'یخچال': { group: 'Cooling', label: 'یخچال' },
  'فریزر': { group: 'Cooling', label: 'فریزر' },
  'یخچال فریزر ساید بای ساید': { group: 'Cooling', label: 'ساید بای ساید' },
  'یخچال فریزر دوقلو': { group: 'Cooling', label: 'دوقلو' },
  'یخچال فریزر بالاپایین': { group: 'Cooling', label: 'بالاپایین' },

  // Washing
  'ماشین لباسشویی': { group: 'Washing', label: 'لباسشویی' },
  'ماشین ظرفشویی': { group: 'Washing', label: 'ظرفشویی' },
  'خشک کن': { group: 'Washing', label: 'خشک‌کن' },

  // Small Appliances
  'جارو برقی': { group: 'Small', label: 'جاروبرقی' },
  'جارو شارژی': { group: 'Small', label: 'جاروشارژی' },
  'اتو و بخارگر': { group: 'Small', label: 'اتو' },
  'چای ساز': { group: 'Small', label: 'چای‌ساز' },
  'قهوه و اسپرسو ساز': { group: 'Small', label: 'قهوه‌ساز' },

  // Spare Parts
  'لوازم یدکی جارو برقی، جاروشارژی و بخارشوی': { group: 'Parts', label: 'لوازم یدکی جارو' },
} as const;

export type CategoryKey = keyof typeof BOSCH_CATEGORIES;
export type CategoryGroup = 'Cooking' | 'Cooling' | 'Washing' | 'Small' | 'Parts';

export function getCategoryGroup(category: string): CategoryGroup | 'Other' {
  const mapping = BOSCH_CATEGORIES[category as CategoryKey];
  return mapping?.group || 'Other';
}

// Helper to construct Torob URL from product_id.
export function buildTorobUrl(torobProductId: string): string {
  return `https://torob.com/p/${torobProductId}`;
}

// The backend does NOT return a `category` field, so the adapter infers it from
// the SKU + title using keyword heuristics. This is FRONTEND-derived data.
const CATEGORY_RULES: Array<[RegExp, string]> = [
  [/ظرفشویی/i, 'ماشین ظرفشویی'],
  [/لباسشویی|واش|washing/i, 'ماشین لباسشویی'],
  [/یخچال.*ساید/i, 'یخچال فریزر ساید بای ساید'],
  [/یخچال.*دوقلو/i, 'یخچال فریزر دوقلو'],
  [/یخچال.*بالاپایین/i, 'یخچال فریزر بالاپایین'],
  [/یخچال/i, 'یخچال'],
  [/فریزر/i, 'فریزر'],
  [/خشک.?کن|خشک کن/i, 'خشک کن'],
  [/هود/i, 'هود آشپزخانه'],
  [/فر\b|[فر]? توکار|فر گازی/i, 'فر برقی و گازی'],
  [/اجاق گاز|گاز/i, 'اجاق گاز'],
  [/جارو شارژی/i, 'جارو شارژی'],
  [/جارو برقی|جاروی/i, 'جارو برقی'],
  [/قهوه|اسپرسو/i, 'قهوه و اسپرسو ساز'],
  [/چای ساز/i, 'چای ساز'],
  [/اتو/i, 'اتو و بخارگر'],
];

/** Infer a Bosch category label from SKU + title (backend has no category). */
export function inferCategory(sku: string | null, title: string | null): string {
  const haystack = `${sku ?? ''} ${title ?? ''}`;
  for (const [re, label] of CATEGORY_RULES) {
    if (re.test(haystack)) return label;
  }
  return 'دسته‌بندی نشده';
}
