import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Package, DollarSign } from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'نمای کلی بازار' },
  { to: '/products', icon: Package, label: 'محصولات' },
  { to: '/margins', icon: DollarSign, label: 'حاشیه سود' },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-white border-l border-slate-200 flex flex-col shrink-0">
      <div className="p-6 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-800">Market Intelligence</h1>
        <p className="text-xs text-slate-400 mt-1">Bosch Market Dashboard</p>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
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
    </aside>
  );
}