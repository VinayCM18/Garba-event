import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Ticket,
  QrCode,
  ClipboardList,
  Sliders,
  ShieldAlert,
  ShieldCheck,
  LogOut,
  ExternalLink,
  Sparkles,
  ChevronRight
} from 'lucide-react';
import { adminLogout } from '../services/api';
import { useToast } from './Toast';

interface AdminSidebarProps {
  onCloseMobile?: () => void;
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({ onCloseMobile }) => {
  const navigate = useNavigate();
  const { info } = useToast();

  const userJson = localStorage.getItem('admin_user');
  const user = userJson ? JSON.parse(userJson) : null;
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';

  const handleLogout = async () => {
    await adminLogout();
    info('Logged out', 'You have been securely logged out.');
    navigate('/management');
  };

  const navItems = [
    { name: 'Dashboard', path: '/admin', icon: LayoutDashboard },
    { name: 'Payment Verification', path: '/admin/verification', icon: ShieldCheck, badge: 'UPI' },
    { name: 'Bookings & Sales', path: '/admin/bookings', icon: Ticket },
    { name: 'QR Gate Scanner', path: '/admin/scanner', icon: QrCode, badge: 'Camera' },
    { name: 'Check-in Logs', path: '/admin/checkins', icon: ClipboardList },
    ...(isSuperAdmin ? [{ name: 'Event Settings', path: '/admin/settings', icon: Sliders }] : []),
    { name: 'Audit Logs', path: '/admin/audit-logs', icon: ShieldAlert },
  ];

  return (
    <aside className="w-64 bg-[#0f0c1b] border-r border-white/5 flex flex-col h-full shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-6 border-b border-white/[0.08] flex items-center gap-3">
        <div className="w-10 h-10 rounded-full overflow-hidden border border-[#d4af37]/50 shadow-md shadow-[#d4af37]/20 bg-[#07080d] shrink-0">
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
          <div className="text-[10px] text-slate-400 font-semibold tracking-widest uppercase">
            Executive Portal
          </div>
        </div>
      </div>

      {/* User profile card */}
      <div className="px-4 py-3 mx-3 my-3 rounded-xl bg-white/[0.02] border border-white/[0.08] flex items-center justify-between">
        <div className="truncate">
          <div className="text-xs font-bold text-slate-200 truncate">{user?.name || 'Administrator'}</div>
          <div className="text-[10px] text-slate-400 truncate">{user?.email || 'admin@garbanight.local'}</div>
        </div>
        <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-[#d4af37]/15 text-[#f3e4b2] border border-[#d4af37]/30">
          {user?.role || 'ADMIN'}
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
              end={item.path === '/admin'}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-[#d4af37]/15 text-[#f3e4b2] border border-[#d4af37]/35 shadow-sm'
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

      {/* Bottom utility links */}
      <div className="p-3 border-t border-white/5 space-y-1">
        <a
          href="/"
          target="_blank"
          rel="noreferrer"
          className="flex items-center justify-between px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-white/[0.03] transition-colors"
        >
          <div className="flex items-center gap-2">
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open Public Site</span>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        </a>

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
