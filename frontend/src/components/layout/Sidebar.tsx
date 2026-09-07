import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Package, DollarSign, Truck, X } from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'نمای کلی بازار' },
  { to: '/products', icon: Package, label: 'محصولات' },
  { to: '/margins', icon: DollarSign, label: 'حاشیه سود' },
  { to: '/shipments', icon: Truck, label: 'محموله‌ها' },
];

interface SidebarProps {
  /** Called to close the mobile drawer (optional — desktop sidebar has no close button). */
  onClose?: () => void;
}

/** Navigation sidebar. Fixed on desktop; slides in as a drawer on mobile. */
export function Sidebar({ onClose }: SidebarProps) {
  return (
    <div className="flex flex-col h-full w-64 bg-white border-l border-slate-200">
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Market Intelligence</h1>
            <p className="text-xs text-slate-400 mt-1">Bosch Market Dashboard</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="md:hidden p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              aria-label="بستن منو"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-slate-600 hover:bg-slate-50'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}