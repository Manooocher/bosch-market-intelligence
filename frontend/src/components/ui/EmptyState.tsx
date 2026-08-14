import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <div className="text-slate-300">
        {icon ?? <Inbox className="w-12 h-12" />}
      </div>
      <h3 className="text-lg font-medium text-slate-600">{title}</h3>
      {description && <p className="text-sm text-slate-400 max-w-md">{description}</p>}
    </div>
  );
}