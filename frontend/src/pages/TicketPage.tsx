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

  let offerType = 'STAG ENTRY';
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

        {/* 2. Main Ticket Body: Left (Cartouche + Details), Right (Stub + QR) */}
        <div className="grid grid-cols-1 md:grid-cols-12 relative">
          {/* Left / Center Section (approx 8 cols) */}
          <div className="md:col-span-8 p-5 sm:p-6 flex flex-col justify-between gap-5 relative z-10">
            {/* Scalloped Royal Ivory Arch Cartouche */}
            <div className="bg-[#FFF9E8] border-2 border-[#D4AF37] rounded-2xl p-4 sm:p-5 text-center shadow-md relative overflow-hidden">
              <div className="text-[10px] sm:text-xs font-black text-[#460F19] uppercase tracking-widest">
                ENTRY PASS
              </div>
              <div className="text-2xl sm:text-3xl font-black text-[#460F19] font-['Cinzel'] tracking-wider mt-1">
                {phaseName}
              </div>
              <div className="text-[11px] sm:text-xs font-bold text-[#B45309] uppercase tracking-wider mt-1">
                ❖ {offerType} ❖
              </div>
            </div>

            {/* Event Details Grid (Date, Time, Gate, Venue) */}
            <div className="space-y-3.5 text-xs sm:text-sm text-[#FFF8E8]">
              <div className="flex items-start gap-3">
                <span className="text-base sm:text-lg">📅</span>
                <div>
                  <div className="font-extrabold tracking-wide text-white sm:text-base">
                    {config?.event_date || '17 OCT 2026'}
                  </div>
                  <div className="text-[11px] text-[#F3E4B2]">Official Gala Night</div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-base sm:text-lg">🕐</span>
                <div>
                  <div className="font-extrabold tracking-wide text-white sm:text-base">
                    {config?.event_time || '06:30 PM - 10:00 PM'}
                  </div>
                  <div className="text-xs font-black text-[#FBBF24]">
                    Gate Opening: 5:30 PM
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-base sm:text-lg">📍</span>
                <div>
                  <div className="font-extrabold tracking-wide text-white sm:text-base uppercase">
                    {config?.venue_name || 'GREEN ACRES'}
                  </div>
                  <div className="text-[11px] text-[#F3E4B2]">
                    {config?.venue_address || 'Green Acres, Mysuru'}
                  </div>
                </div>
              </div>
            </div>

            {/* Attendee info badge */}
            <div className="p-3 rounded-xl bg-black/40 border border-[#D4AF37]/30 flex items-center justify-between text-xs">
              <div>
                <div className="text-[9px] uppercase font-bold text-[#F3E4B2]/70">ATTENDEE NAME</div>
                <div className="text-sm font-black text-white truncate max-w-[200px] sm:max-w-none">{ticket.customer_name}</div>
              </div>
              <div className="text-right">
                <div className="text-[9px] uppercase font-bold text-[#F3E4B2]/70">STATUS</div>
                <div className="text-xs font-bold text-emerald-400 flex items-center gap-1 justify-end">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>{isUsed ? 'CHECKED IN' : isCancelled ? 'CANCELLED' : 'VALID ENTRY'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Section: Tear-off Stub (approx 4 cols) */}
          <div className="md:col-span-4 p-5 sm:p-6 bg-[#350A11] border-t-2 md:border-t-0 md:border-l-2 border-dashed border-[#D4AF37] flex flex-col items-center justify-center text-center relative">
            {/* Perforation Seam Cutout Notches */}
            <div className="hidden md:block absolute -top-3 -left-3 w-6 h-6 rounded-full bg-[#0a0a0c] border border-[#D4AF37]/30" />
            <div className="hidden md:block absolute -bottom-3 -left-3 w-6 h-6 rounded-full bg-[#0a0a0c] border border-[#D4AF37]/30" />

            <div className="text-[10px] sm:text-xs font-extrabold uppercase tracking-widest text-[#F3E4B2]">
              ENTRY PASS
            </div>
            <div className="text-sm font-black text-[#FBBF24] font-['Cinzel'] tracking-wider mt-0.5">
              {phaseName}
            </div>
            <div className="text-[10px] font-bold text-white uppercase tracking-wider">
              {offerType}
            </div>

            <div className="text-xs text-[#D4AF37] my-1">
              ✦ ❖ ✦
            </div>

            <div className="text-[9px] uppercase font-bold tracking-widest text-[#F3E4B2]/70">
              TICKET NO.
            </div>
            <div className="text-xs sm:text-sm font-black font-mono text-white tracking-wider mb-3">
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

            <div className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-[#FFF8E8] mt-2.5">
              SCAN TO VERIFY
            </div>
            <div className="text-[10px] text-[#F3E4B2]/80 mt-1">
              Admit 1 Person
            </div>
          </div>
        </div>

        {/* 3. Sponsor Strip (Location Partner: Green Acres, Main Sponsor, Co-Sponsor - Zero gray circles) */}
        <div className="bg-[#FAF3E0] border-t border-[#D4AF37] p-3 sm:p-3.5 text-[#460F19]">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs divide-x divide-[#460F19]/15">
            <div className="px-2">
              <div className="text-[8px] sm:text-[9px] font-black uppercase text-[#78350F] tracking-wider">LOCATION PARTNER</div>
              <div className="text-[11px] sm:text-xs font-black text-[#460F19] mt-0.5">GREEN ACRES</div>
            </div>
            <div className="px-2">
              <div className="text-[8px] sm:text-[9px] font-black uppercase text-[#78350F] tracking-wider">MAIN SPONSOR</div>
              <div className="text-[10px] sm:text-[11px] font-black text-[#460F19] mt-0.5">HERITAGE PRODUCTIONS</div>
            </div>
            <div className="px-2">
              <div className="text-[8px] sm:text-[9px] font-black uppercase text-[#78350F] tracking-wider">CO-SPONSOR</div>
              <div className="text-[10px] sm:text-[11px] font-black text-[#460F19] mt-0.5">THE HAPPY CIRCLE</div>
            </div>
            <div className="px-2">
              <div className="text-[8px] sm:text-[9px] font-black uppercase text-[#78350F] tracking-wider">PASS STATUS</div>
              <div className="text-[10px] sm:text-[11px] font-black text-[#15803D] mt-0.5">✓ VALID ENTRY</div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
