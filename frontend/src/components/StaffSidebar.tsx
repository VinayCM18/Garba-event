import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  QrCode,
  Search,
  ClipboardList,
  LogOut,
  Sparkles
} from 'lucide-react';
import { adminLogout } from '../services/api';
import { useToast } from './Toast';

interface StaffSidebarProps {
  onCloseMobile?: () => void;
}

export const StaffSidebar: React.FC<StaffSidebarProps> = ({ onCloseMobile }) => {
  const navigate = useNavigate();
  const { info } = useToast();

  const userJson = localStorage.getItem('admin_user');
  const user = userJson ? JSON.parse(userJson) : null;

  const handleLogout = async () => {
    await adminLogout();
    info('Logged Out', 'You have been securely logged out.');
    navigate('/management');
  };

  const navItems = [
    { name: 'Dashboard', path: '/staff', icon: LayoutDashboard },
    { name: 'Scan Ticket', path: '/staff/scanner', icon: QrCode, badge: 'Camera' },
    { name: 'Search Booking', path: '/staff/search', icon: Search },
    { name: 'Check-ins', path: '/staff/checkins', icon: ClipboardList },
  ];

  return (
    <aside className="w-64 bg-[#0c0d16] border-r border-white/5 flex flex-col h-full shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-6 border-b border-white/[0.08] flex items-center gap-3">
        <div className="w-10 h-10 rounded-full overflow-hidden border border-[#d4af37]/40 shadow-md shadow-[#d4af37]/20 bg-[#07080d]">
          <img
            src="/heritage_productions.jpg"
            alt="Heritage Productions"
            className="w-full h-full object-cover"
          />
        </div>
        <div>
          <div className="font-extrabold text-sm tracking-[0.08em] bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent font-['Cinzel']">
            NAVRANG 2026
          </div>
          <div className="text-[10px] text-emerald-400 font-semibold tracking-widest uppercase">
            Staff Gate Console
          </div>
        </div>
      </div>

      {/* User profile card */}
      <div className="px-4 py-3 mx-3 my-3 rounded-xl bg-white/[0.02] border border-white/[0.08] flex items-center justify-between">
        <div className="truncate">
          <div className="text-xs font-bold text-slate-200 truncate">{user?.name || 'Gate Staff'}</div>
          <div className="text-[10px] text-slate-400 truncate">{user?.email || 'staff@garbanight.in'}</div>
        </div>
        <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          STAFF
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/staff'}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/35 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Logout button */}
      <div className="p-3 border-t border-white/5">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
