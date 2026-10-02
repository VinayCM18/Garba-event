import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Download,
  Printer,
  Calendar,
  Clock,
  MapPin,
  XCircle,
  ArrowLeft,
  Image as ImageIcon
} from 'lucide-react';
import { fetchTicketByToken, fetchPublicConfig, getDownloadUrl } from '../services/api';
import { Ticket, EventConfig } from '../types';

export const TicketPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [config, setConfig] = useState<EventConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    fetchPublicConfig().then(setConfig).catch(() => {});

    if (!token) return;

    fetchTicketByToken(token)
      .then((data) => {
        setTicket(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching ticket:', err);
        setErrorMsg('Invalid or expired ticket link.');
        setLoading(false);
      });
  }, [token]);

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-10 h-10 border-3 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400">Loading digital entry pass...</p>
      </div>
    );
  }

  if (errorMsg || !ticket) {
    return (
      <div className="py-24 px-4 text-center max-w-md mx-auto">
        <XCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-white mb-1">Ticket Not Found</h2>
        <p className="text-xs text-slate-400 mb-6">{errorMsg || 'Could not verify ticket token.'}</p>
        <Link to="/" className="festive-button px-5 py-2 rounded-full text-xs font-bold inline-block">
          Return to Home
        </Link>
      </div>
    );
  }

  const isUsed = ticket.checkin_status || ticket.ticket_status === 'USED';
  const isCancelled = ticket.ticket_status === 'CANCELLED';

  // Dynamic Phase and Offer Title determination
  const combinedOffer = ((ticket as any).offer_title || (ticket as any).offer_id || '').toLowerCase();
  const isEarly = combinedOffer.includes('early');
  const isPhase1 = combinedOffer.includes('phase 1') || combinedOffer.includes('phase_1');
  const phaseName = isEarly ? 'EARLY BIRD' : isPhase1 ? 'PHASE 1' : 'EARLY BIRD';

  let offerType = 'SINGLE ENTRY';
  if (combinedOffer.includes('group')) {
    offerType = 'GROUP OF 10';
  } else if (combinedOffer.includes('couple')) {
    offerType = 'COUPLE ENTRY';
  } else if (combinedOffer.includes('kid') || combinedOffer.includes('child')) {
    offerType = 'KIDS ENTRY';
  }

  const qrSrc = ticket.qr_code_base64
    ? (ticket.qr_code_base64.startsWith('data:') ? ticket.qr_code_base64 : `data:image/png;base64,${ticket.qr_code_base64}`)
    : `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(ticket.qr_token_raw || ticket.ticket_id)}&color=0f0c20&bgcolor=ffffff`;

  return (
    <div className="py-10 px-4 sm:px-6 max-w-4xl mx-auto">
      {/* Top back navigation & actions */}
      <div className="flex items-center justify-between mb-6">
        <Link to="/" className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Home</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
          <a
            href={getDownloadUrl(`/api/tickets/${ticket.ticket_id}/pass.jpg?token=${encodeURIComponent(ticket.qr_token_raw || '')}`)}
            download={`NAVRANG2026_Pass_${ticket.ticket_id}.jpg`}
            className="px-3.5 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-xs font-semibold text-[#f3e4b2] flex items-center gap-1.5 transition-colors"
          >
            <ImageIcon className="w-3.5 h-3.5 text-amber-400" />
            <span>Pass Image</span>
          </a>
          <a
            href={getDownloadUrl(`/api/tickets/${ticket.ticket_id}/pdf?token=${encodeURIComponent(ticket.qr_token_raw || '')}`)}
            download
            className="festive-button px-4 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md shadow-amber-500/20"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF Pass</span>
          </a>
        </div>
      </div>

      {/* Official NAVRANG 2026 Ticket Pass Matching Reference Image */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-[#3D0C14] border-2 border-[#D4AF37] shadow-2xl overflow-hidden text-white relative print:border-black print:text-black"
        style={{
          boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 25px rgba(212,175,55,0.2)'
        }}
      >
        {/* Subtle decorative inner border */}
        <div className="absolute inset-1.5 sm:inset-2.5 border border-[#D4AF37]/30 rounded-2xl pointer-events-none" />

        {/* 1. Header Banner: Collaboration Logos & Branding */}
        <div className="bg-[#2E080E] p-4 sm:p-5 text-center relative border-b border-[#D4AF37]/30">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-full p-0.5 bg-black/60 border border-[#D4AF37]/60 overflow-hidden shrink-0 shadow-md">
              <img
                src="/heritage_productions.jpg"
                alt="Heritage Productions"
                className="w-full h-full object-cover rounded-full"
              />
            </div>
            <span className="text-[#FBBF24] text-xs sm:text-sm font-bold">✕</span>
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-full p-0.5 bg-black/60 border border-[#D4AF37]/60 overflow-hidden shrink-0 shadow-md">
              <img
                src="/images/happy-circle-logo.png"
                alt="The Happy Circle"
                className="w-full h-full object-cover rounded-full"
              />
            </div>
          </div>

          <div className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.2em] text-[#FBBF24]">
            HERITAGE PRODUCTIONS &nbsp;×&nbsp; THE HAPPY CIRCLE
          </div>

          {/* Central NAVRANG DANDIYA 2026 title */}
          <div className="mt-2 text-3xl sm:text-5xl font-black tracking-wider uppercase font-['Cinzel'] text-transparent bg-clip-text bg-gradient-to-b from-[#FFE082] via-[#FFD54F] to-[#FFB300] drop-shadow-lg">
            NAVRANG
          </div>
          <div className="text-xs sm:text-sm font-extrabold uppercase tracking-widest text-[#FCD34D] mt-0.5 flex items-center justify-center gap-2">
            <span>🔔</span>
            <span>DANDIYA 2026</span>
            <span>🔔</span>
          </div>
        </div>

        {/* 2. Main Ticket Body: Left (Perks & Attendee), Right (Stub + QR + Event Details) */}
        <div className="grid grid-cols-1 md:grid-cols-12 relative">
          {/* Left / Center Section: Festival Perks & Attendee Details (Centered and Non-duplicated) */}
          <div className="md:col-span-7 p-5 sm:p-6 flex flex-col justify-center gap-5 relative z-10">
            {/* Festival Perks Card */}
            <div className="bg-[#2E080E] border border-[#D4AF37]/40 rounded-2xl p-5 sm:p-6 text-center shadow-md relative overflow-hidden flex flex-col items-center justify-center">
              <div className="text-[10px] sm:text-xs font-black text-[#FBBF24] uppercase tracking-widest">
                = FESTIVAL PERKS =
              </div>
              <div className="text-xl sm:text-2xl font-black text-white font-['Cinzel'] tracking-wider mt-2">
                LIVE GUJARATI DHOL
              </div>
              <div className="text-xs text-[#F3E4B2] mt-1.5">
                DJ Night • Dandiya Raas • 360° Booth
              </div>
              <div className="text-xs font-bold text-[#FBBF24] mt-2">
                Complimentary Food Voucher Included
              </div>

              {/* Centered Divider */}
              <div className="w-4/5 border-t border-dashed border-[#D4AF37]/30 my-4" />

              {/* Pass Holder & Admission Details - Perfectly Centered */}
              <div className="text-[10px] uppercase font-bold text-[#F3E4B2]/80 tracking-wider">
                PASS HOLDER
              </div>
              <div className="text-base sm:text-lg font-black text-white tracking-wide mt-0.5">
                {ticket.customer_name}
              </div>

              <div className="text-xs font-extrabold text-emerald-400 mt-3">
                = ADMIT 1 PERSON =
              </div>
              <div className="text-[10px] font-bold text-[#F3E4B2]/80 mt-0.5 tracking-wider">
                NON-TRANSFERABLE
              </div>
            </div>

            {/* Admission status badge */}
            <div className="p-3 rounded-xl bg-black/40 border border-[#D4AF37]/30 flex items-center justify-between text-xs">
              <span className="text-[10px] uppercase font-bold text-[#F3E4B2]/70">ENTRY STATUS</span>
              <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>{isUsed ? 'CHECKED IN' : isCancelled ? 'CANCELLED' : 'VALID ADMISSION PASS'}</span>
              </span>
            </div>
          </div>

          {/* Right Section: Authoritative Single Admission Panel */}
          <div className="md:col-span-5 p-5 sm:p-6 bg-[#350A11] border-t-2 md:border-t-0 md:border-l-2 border-dashed border-[#D4AF37] flex flex-col items-center justify-center text-center relative">
            {/* Perforation Seam Cutout Notches */}
            <div className="hidden md:block absolute -top-3 -left-3 w-6 h-6 rounded-full bg-[#0a0a0c] border border-[#D4AF37]/30" />
            <div className="hidden md:block absolute -bottom-3 -left-3 w-6 h-6 rounded-full bg-[#0a0a0c] border border-[#D4AF37]/30" />

            <div className="text-[10px] sm:text-xs font-extrabold uppercase tracking-widest text-[#F3E4B2]">
              ENTRY PASS
            </div>
            <div className="text-base sm:text-lg font-black text-[#FBBF24] font-['Cinzel'] tracking-wider mt-0.5">
              {phaseName}
            </div>
            <div className="text-xs font-bold text-white uppercase tracking-wider">
              {offerType}
            </div>

            <div className="text-xs text-[#D4AF37] my-1">
              ✦ ❖ ✦
            </div>

            <div className="text-[9px] uppercase font-bold tracking-widest text-[#F3E4B2]/70">
              TICKET NO.
            </div>
            <div className="text-xs sm:text-sm font-black font-mono text-white tracking-wider mb-2.5">
              {ticket.ticket_id}
            </div>

            {/* High-Contrast Pure White QR Box */}
            <div className="p-2 sm:p-2.5 bg-white rounded-xl shadow-lg border border-slate-300 inline-block">
              <img
                src={qrSrc}
                alt="Entry QR Code"
                className="w-32 h-32 sm:w-36 sm:h-36 object-contain block"
              />
            </div>

            <div className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-[#FFF8E8] mt-2">
              SCAN TO VERIFY
            </div>

            {/* Event Details: Date, Time, Gate, Venue (Rendered EXACTLY ONCE) */}
            <div className="mt-3 pt-3 border-t border-[#D4AF37]/30 w-full space-y-1 text-center">
              <div className="text-xs font-black text-white flex items-center justify-center gap-1.5">
                <span>📅</span>
                <span>{config?.event_date || '17 OCT 2026'}</span>
              </div>
              <div className="text-[11px] text-[#F3E4B2] flex items-center justify-center gap-1.5">
                <span>🕐</span>
                <span>{config?.event_time || '06:30 PM - 10:00 PM'}</span>
              </div>
              <div className="text-[11px] font-black text-[#FBBF24]">
                Gate Opening: 05:30 PM
              </div>
              <div className="text-xs font-black text-white uppercase mt-1 flex items-center justify-center gap-1.5">
                <span>📍</span>
                <span>{config?.venue_name || 'The Green Acres'}</span>
              </div>
              <div className="text-[10px] text-[#F3E4B2]">
                Mysuru
              </div>
            </div>
          </div>
        </div>

        {/* 3. New Bottom Branding / Sponsor Section (3-Column Layout with Gold Dividers) */}
        <div className="bg-[#000000] border-t-2 border-[#D4AF37] p-4 text-center">
          <div className="grid grid-cols-1 md:grid-cols-12 items-center gap-4 text-center">
            {/* Left: Happy Circle Logo */}
            <div className="md:col-span-3 flex flex-col items-center justify-center border-b md:border-b-0 md:border-r border-[#D4AF37]/40 pb-3 md:pb-0 md:pr-4">
              <span className="text-[9px] uppercase font-bold tracking-widest text-[#F3E4B2]/70 mb-1.5">
                CURATED BY
              </span>
              <img
                src="/images/happy-circle-logo.png"
                alt="The Happy Circle"
                className="h-10 sm:h-11 w-auto object-contain mx-auto"
              />
              <span className="text-[10px] font-bold text-[#FFF8E8] mt-1.5">
                The Happy Circle
              </span>
            </div>

            {/* Center: Partners / Collaboration */}
            <div className="md:col-span-6 flex flex-col items-center justify-center px-2 py-1">
              <div className="text-xs sm:text-sm font-black font-['Cinzel'] text-[#FFF8E8]">
                Heritage Production × The Happy Circle
              </div>
              <div className="text-[10px] sm:text-xs font-semibold text-[#F3E4B2] mt-1">
                Production partner Wedeos Entertainment
              </div>
            </div>

            {/* Right: Wedeos Entertainment Logo */}
            <div className="md:col-span-3 flex flex-col items-center justify-center border-t md:border-t-0 md:border-l border-[#D4AF37]/40 pt-3 md:pt-0 md:pl-4">
              <span className="text-[9px] uppercase font-bold tracking-widest text-[#F3E4B2]/70 mb-1.5">
                PRODUCTION PARTNER
              </span>
              <img
                src="/images/wedeos-logo.jpg"
                alt="Wedeos Entertainment"
                className="h-9 sm:h-10 w-auto object-contain mx-auto"
              />
              <span className="text-[10px] font-bold text-[#FFF8E8] mt-1.5">
                Wedeos Entertainment
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
