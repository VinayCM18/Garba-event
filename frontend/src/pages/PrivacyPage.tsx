import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export const PrivacyPage: React.FC = () => {
  return (
    <div className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-slate-300 space-y-8">
      <Link to="/" className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5">
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Home</span>
      </Link>

      <div>
        <h1 className="text-3xl sm:text-4xl font-black text-white font-['Outfit']">Privacy Policy</h1>
        <p className="text-xs text-slate-400 mt-1">NAVRANG 2026 • Official Ticketing Platform</p>
      </div>

      <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-6 text-xs sm:text-sm leading-relaxed border border-white/10">
        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">1. Information We Collect</h2>
          <p>
            When purchasing event passes, we collect your full name, email address, mobile number, and transaction identifiers. We do NOT store payment card details, UPI PINs, or bank account credentials on our servers; all payment transactions are handled directly through Razorpay's PCI-DSS compliant infrastructure.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">2. Use of Information</h2>
          <p>
            Your information is used solely to generate digital entry passes, transmit confirmation emails, manage venue security admissions, and notify you regarding critical event schedule updates.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">3. Data Security & QR Cryptography</h2>
          <p>
            We implement cryptographic salts and SHA-256 token hashing. Database records do not expose readable tokens, ensuring unauthorized third parties cannot reverse-engineer or duplicate your passes.
          </p>
        </section>
      </div>
    </div>
  );
};
