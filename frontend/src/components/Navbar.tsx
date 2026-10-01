import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Ticket, Menu, X, Sparkles } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { name: 'Home', href: '/#hero' },
    { name: 'Event', href: '/#about' },
    { name: 'Tickets', href: '/#pricing' },
    { name: 'About', href: '/#highlights' },
    { name: 'Contact', href: '/#venue' },
  ];

  return (
    <header
      className={`sticky top-0 z-40 w-full border-b transition-all duration-300 ${
        scrolled
          ? 'h-16 bg-[#080309]/95 border-[#d4af37]/20 shadow-xl shadow-black/60 backdrop-blur-xl'
          : 'h-20 bg-[#080309]/85 border-white/[0.08] backdrop-blur-md'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
        {/* Brand: NAVRANG × THE HAPPY CIRCLE */}
        <Link to="/" className="flex items-center gap-2.5 sm:gap-3 group shrink-0">
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Logo 1: Heritage Productions */}
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full overflow-hidden border border-[#d4af37]/60 shadow-[0_0_10px_rgba(212,175,55,0.3)] group-hover:scale-105 transition-transform bg-black flex items-center justify-center shrink-0">
              <img
                src="/heritage_productions.jpg"
                alt="Heritage Productions"
                className="w-full h-full object-cover"
              />
            </div>
            <span className="text-[11px] sm:text-xs text-[#d4af37] font-black font-mono">×</span>
            {/* Logo 2: The Happy Circle */}
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-full overflow-hidden border border-[#d4af37]/60 shadow-[0_0_10px_rgba(212,175,55,0.3)] group-hover:scale-105 transition-transform bg-black flex items-center justify-center shrink-0">
              <img
                src="/images/happy-circle-logo.png"
                alt="The Happy Circle"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg sm:text-xl font-extrabold tracking-[0.08em] bg-gradient-to-r from-white via-[#f7e8c3] to-[#d4af37] bg-clip-text text-transparent uppercase font-['Cinzel']">
                NAVRANG
              </span>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#d4af37]/15 text-[#f7e8c3] border border-[#d4af37]/35 tracking-wider font-['Cinzel']">
                2026
              </span>
            </div>
            <p className="text-[10px] text-[#e5c97b]/90 tracking-[0.14em] uppercase font-bold font-['Plus_Jakarta_Sans']">
              in collab with The Happy Circle
            </p>
          </div>
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-7 lg:gap-8">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              className="text-xs font-semibold uppercase tracking-wider text-slate-300 hover:text-[#f7e8c3] transition-colors py-2 relative group"
            >
              {link.name}
              <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-[#d4af37] transition-all group-hover:w-full" />
            </a>
          ))}
        </nav>

        {/* Desktop Primary CTA Button */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            to="/book"
            className="festive-button flex items-center gap-2 px-6 py-2.5 rounded-full text-xs font-black tracking-wider uppercase shadow-lg shadow-[#d4af37]/25"
          >
            <Ticket className="w-4 h-4" />
            <span>BOOK TICKETS</span>
          </Link>
        </div>

        {/* Mobile Actions: Fast Book + Clean Hamburger */}
        <div className="flex md:hidden items-center gap-2.5">
          <Link
            to="/book"
            className="festive-button px-4 py-2 rounded-full text-xs font-black uppercase tracking-wider touch-target"
          >
            Book
          </Link>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="p-2.5 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 touch-target focus:outline-none focus:ring-1 focus:ring-[#d4af37]/50"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="w-6 h-6 text-[#f7e8c3]" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer (Clean, Large Touch Targets, No Admin/Staff links) */}
      {mobileOpen && (
        <div className="md:hidden border-b border-[#d4af37]/20 bg-[#0c0510]/98 backdrop-blur-2xl px-5 pt-4 pb-7 space-y-2 shadow-2xl">
          <div className="text-[10px] uppercase font-bold tracking-[0.2em] text-[#d4af37] mb-2 px-3">
            Navigation Menu
          </div>
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold text-slate-200 hover:bg-white/5 hover:text-[#f7e8c3] transition-colors touch-target"
            >
              <span>{link.name}</span>
              <span className="text-[#d4af37]/50">→</span>
            </a>
          ))}
          <div className="pt-3 border-t border-white/[0.08]">
            <Link
              to="/book"
              onClick={() => setMobileOpen(false)}
              className="festive-button w-full text-center py-3.5 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl shadow-[#d4af37]/25 touch-target"
            >
              <Ticket className="w-4 h-4" />
              <span>BOOK YOUR TICKETS</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
