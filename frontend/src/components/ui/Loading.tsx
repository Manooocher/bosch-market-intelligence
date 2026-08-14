export function SkeletonRow({ cols = 6 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-200 rounded animate-pulse" style={{ width: `${60 + Math.random() * 40}%` }} />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
      <div className="h-5 bg-slate-200 rounded animate-pulse w-1/3" />
      <div className="h-8 bg-slate-200 rounded animate-pulse w-1/2" />
      <div className="h-4 bg-slate-200 rounded animate-pulse w-2/3" />
    </div>
  );
}

type SpinnerSize = 'sm' | 'md' | 'lg';

const sizeMap: Record<SpinnerSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
};

export function Spinner({ size = 'md' }: { size?: SpinnerSize }) {
  return (
    <div className="flex items-center justify-center p-4">
      <div
        className={`${sizeMap[size]} border-2 border-slate-200 border-t-indigo-600 rounded-full animate-spin`}
      />
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <tbody>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} cols={cols} />
      ))}
    </tbody>
  );
}