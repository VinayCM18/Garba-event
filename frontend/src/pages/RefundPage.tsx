import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export const RefundPage: React.FC = () => {
  return (
    <div className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-slate-300 space-y-8">
      <Link to="/" className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5">
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Home</span>
      </Link>

      <div>
        <h1 className="text-3xl sm:text-4xl font-black text-white font-['Outfit']">Refund & Cancellation Policy</h1>
        <p className="text-xs text-slate-400 mt-1">Official Event Guidelines • Garba Night 2026</p>
      </div>

      <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-6 text-xs sm:text-sm leading-relaxed border border-white/10">
        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">1. Non-Refundable Passes</h2>
          <p>
            All ticket bookings made for Garba Night 2026 are final and strictly non-refundable. Once a booking order is confirmed and tickets are issued, cancellations or refunds cannot be processed under any circumstances, including personal scheduling conflicts or weather variations.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">2. Event Rescheduling</h2>
          <p>
            In the unforeseen event that municipal authorities or severe acts of nature mandate rescheduling the event, all valid entry tickets will be automatically honored on the rescheduled date.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-bold text-white font-['Outfit']">3. Fraudulent & Duplicate Bookings</h2>
          <p>
            Tickets identified as obtained via fraudulent transactions or re-sold through unapproved secondary black-market brokers will be immediately cancelled without refund, and entrance denied at the venue gates.
          </p>
        </section>
      </div>
    </div>
  );
};
