import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, QrCode, Clock, ShieldCheck } from 'lucide-react';

interface AdminHeaderProps {
  title: string;
  onOpenMobileSidebar: () => void;
}

export const AdminHeader: React.FC<AdminHeaderProps> = ({ title, onOpenMobileSidebar }) => {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-16 border-b border-white/5 bg-[#0f0c1b]/80 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-base sm:text-lg font-bold text-white tracking-wide font-['Outfit']">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Live clock */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/5 text-xs font-mono text-slate-400">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>{timeStr || '12:00:00 PM'}</span>
        </div>

        {/* Quick Launch Scanner Button */}
        <Link
          to="/admin/scanner"
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition-all"
        >
          <QrCode className="w-3.5 h-3.5" />
          <span>Scan QR</span>
        </Link>
      </div>
    </header>
  );
};
