import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

export const RulesPage: React.FC = () => {
  return (
    <div className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-slate-300 space-y-8">
      <Link to="/" className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5">
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Home</span>
      </Link>

      <div>
        <h1 className="text-3xl sm:text-4xl font-black text-white font-['Outfit']">Venue Rules & Guidelines</h1>
        <p className="text-xs text-slate-400 mt-1">The Serenity Grove, Mysuru</p>
      </div>

      <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-6 text-xs sm:text-sm leading-relaxed border border-white/10">
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 space-y-1.5">
            <div className="font-bold flex items-center gap-2 text-sm text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              Permitted & Encouraged
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Traditional Navratri festive wear (Chaniya Choli, Kurta Pajama, Kediyu, Dhoti).</li>
              <li>Carrying mobile phone with downloaded digital PDF ticket or high-contrast QR pass.</li>
              <li>Government photo ID (Aadhaar, Driving License, Voter ID) matching the primary attendee.</li>
              <li>Personal wooden or fiber Dandiya sticks (subject to physical security check).</li>
            </ul>
          </div>

          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-200 space-y-1.5">
            <div className="font-bold flex items-center gap-2 text-sm text-rose-400">
              <XCircle className="w-4 h-4" />
              Strictly Prohibited Inside Arena
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Alcohol, narcotics, tobacco, cigarettes, and vapes.</li>
              <li>Outside cooked food, glass bottles, and tin cans.</li>
              <li>Sharp metallic objects, knives, weapons, or fireworks.</li>
              <li>Commercial video cameras, drones, and unaccredited media rigs.</li>
            </ul>
          </div>

          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-200 space-y-1.5">
            <div className="font-bold flex items-center gap-2 text-sm text-amber-400">
              <AlertTriangle className="w-4 h-4" />
              Turnstile Entry Protocols
            </div>
            <p className="text-xs">
              Entry starts promptly at 05:30 PM. Event runs from 06:00 PM onwards till 10:00 PM. Each attendee must scan their individual QR code at the optical scanner turnstiles. Re-entry after leaving the arena grounds is strictly forbidden.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
