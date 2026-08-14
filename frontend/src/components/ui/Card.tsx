type CardPadding = 'sm' | 'md' | 'lg';

const paddingMap: Record<CardPadding, string> = {
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6',
};

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: CardPadding;
}

export function Card({ children, className = '', padding = 'md' }: CardProps) {
  return (
    <div
      className={`bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition ${paddingMap[padding]} ${className}`}
    >
      {children}
    </div>
  );
}