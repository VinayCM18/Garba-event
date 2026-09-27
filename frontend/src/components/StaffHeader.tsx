import React from 'react';
import { Menu, QrCode } from 'lucide-react';
import { Link } from 'react-router-dom';

interface StaffHeaderProps {
  title: string;
  onOpenMobileSidebar: () => void;
}

export const StaffHeader: React.FC<StaffHeaderProps> = ({ title, onOpenMobileSidebar }) => {
  return (
    <header className="h-16 border-b border-white/[0.08] bg-[#0c0d16]/80 backdrop-blur-xl px-4 sm:px-6 flex items-center justify-between z-10 shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="p-2 -ml-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-base sm:text-lg font-bold text-white font-['Outfit'] tracking-wide">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <Link
          to="/staff/scanner"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-bold transition-all"
        >
          <QrCode className="w-4 h-4" />
          <span className="hidden sm:inline">Launch Scanner</span>
        </Link>
      </div>
    </header>
  );
};
