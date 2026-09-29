import React from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Mail, Phone, MapPin, Heart, ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-white/[0.08] bg-[#06070c] pt-16 pb-12 text-slate-400 text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="space-y-4 md:col-span-1">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full overflow-hidden border border-[#d4af37]/50 shadow-md shadow-[#d4af37]/20 bg-black flex items-center justify-center p-0.5 shrink-0">
                <img
                  src="/images/happy-circle-logo.png"
                  alt="The Happy Circle Logo"
                  className="w-full h-full object-contain"
                />
              </div>
              <div>
                <span className="text-xl font-extrabold tracking-[0.12em] bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent uppercase font-['Cinzel'] block">
                  NAVRANG 2026
                </span>
                <span className="text-[10px] text-[#e5c97b] font-bold tracking-[0.15em] uppercase block font-['Cinzel']">
                  in collab with The Happy Circle
                </span>
              </div>
            </Link>
            <p className="text-xs text-slate-400 leading-relaxed">
              The premier cultural celebration NAVRANG 2026 at Green Acres, Mysuru in collaboration with The Happy Circle. An unforgettable evening of authentic Garba beats, live music, and encrypted digital entry passes.
            </p>
            <div className="pt-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-3.5 h-3.5" />
                Verified QR E-Ticket Platform
              </span>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-white font-bold text-xs tracking-widest uppercase mb-4 font-['Outfit']">
              Quick Links
            </h4>
            <ul className="space-y-2.5 text-xs">
              <li><Link to="/#about" className="hover:text-[#f3e4b2] transition-colors">About the Gala</Link></li>
              <li><Link to="/#highlights" className="hover:text-[#f3e4b2] transition-colors">Curated Highlights</Link></li>
              <li><Link to="/#pricing" className="hover:text-[#f3e4b2] transition-colors">Pass Pricing</Link></li>
              <li><Link to="/#venue" className="hover:text-[#f3e4b2] transition-colors">Venue & Directions</Link></li>
              <li><Link to="/#faq" className="hover:text-[#f3e4b2] transition-colors">Frequently Asked Questions</Link></li>
            </ul>
          </div>

          {/* Legal Policies */}
          <div>
            <h4 className="text-white font-bold text-xs tracking-widest uppercase mb-4 font-['Outfit']">
              Policies & Rules
            </h4>
            <ul className="space-y-2.5 text-xs">
              <li><Link to="/terms" className="hover:text-[#f3e4b2] transition-colors">Terms & Conditions</Link></li>
              <li><Link to="/privacy" className="hover:text-[#f3e4b2] transition-colors">Privacy Policy</Link></li>
              <li><Link to="/refund" className="hover:text-[#f3e4b2] transition-colors">Refund & Cancellation Policy</Link></li>
              <li><Link to="/rules" className="hover:text-[#f3e4b2] transition-colors">Venue Entry Guidelines</Link></li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="text-white font-bold text-xs tracking-widest uppercase mb-4 font-['Outfit']">
              Event Concierge
            </h4>
            <ul className="space-y-3 text-xs">
              <li className="flex items-start gap-2.5">
                <MapPin className="w-4 h-4 text-[#d4af37] shrink-0 mt-0.5" />
                <span>Green Acres, Mysuru</span>
              </li>
              <li className="flex items-center gap-2.5">
                <Mail className="w-4 h-4 text-[#d4af37] shrink-0" />
                <a href="mailto:Samaymadhyastha2005@gmail.com" className="hover:text-white">Samaymadhyastha2005@gmail.com</a>
              </li>
              <li className="flex items-center gap-2.5">
                <Phone className="w-4 h-4 text-[#d4af37] shrink-0" />
                <a href="tel:7483139146" className="hover:text-white">+91 74831 39146</a>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-white/[0.06] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
          <div>
            © 2026 NAVRANG Official Celebration. In collaboration with The Happy Circle. All rights reserved.
          </div>
          <div className="flex items-center gap-1.5 text-slate-500">
            <span>Official Cultural Gala</span>
            <span>•</span>
            <span className="text-[#d4af37] font-semibold">Navratri 2026</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
