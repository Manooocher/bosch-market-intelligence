import { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';

interface ProductSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
}

/** Debounced search input — only propagates value after the user pauses typing. */
export function ProductSearch({
  value,
  onChange,
  placeholder = 'جستجوی محصول (SKU یا عنوان)…',
  debounceMs = 400,
}: ProductSearchProps) {
  const [input, setInput] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setInput(value);
  }, [value]);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      if (input !== value) onChange(input);
    }, debounceMs);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, debounceMs]);

  return (
    <div className="relative">
      <Search className="absolute top-1/2 -translate-y-1/2 right-3 w-5 h-5 text-slate-400" />
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-4 pr-10 py-2.5 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      />
    </div>
  );
}