import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, ArrowLeft } from 'lucide-react';

export const TermsPage: React.FC = () => {
  return (
    <div className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-slate-300 space-y-8">
      <Link to="/" className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5">
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Home</span>
      </Link>

      <div>
        <h1 className="text-3xl sm:text-4xl font-black text-white font-['Outfit']">Terms & Conditions</h1>
        <p className="text-xs text-slate-400 mt-1">Last updated: October 2026 • NAVRANG 2026</p>
      </div>

      <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-6 text-xs sm:text-sm leading-relaxed border border-white/10">
        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">1. Acceptance of Terms</h2>
          <p>
            By purchasing tickets, attending, or registering on the official NAVRANG 2026 platform, you agree to be bound by these Terms and Conditions, all applicable municipal event regulations, and security protocols.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">2. Digital Ticket & Admission Policy</h2>
          <p>
            Each ticket generates a cryptographically secured QR code. Admission is granted strictly on a single-entry basis. Once a QR pass has been validated at the entrance turnstile, any subsequent scan of the same code or duplicates will trigger an automatic security alarm and be denied entry.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">3. Dress Code & Etiquette</h2>
          <p>
            NAVRANG 2026 is a cultural and festive celebration. Traditional attire (Chaniya Choli, Kurta Pajama, Kediyu, or Dhoti) is mandatory for dance arena access. The organizers reserve the absolute right to refuse admission to individuals in non-compliant attire.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">4. Safety, Prohibited Items & Security Screening</h2>
          <p>
            Security frisking and baggage inspection are mandatory upon entrance. Strictly prohibited items include: alcohol, drugs, weapons, sharp objects, outside food and beverages, and unauthorized commercial recording equipment.
          </p>
        </section>
      </div>
    </div>
  );
};
