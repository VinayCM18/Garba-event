import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Download,
  Printer,
  Calendar,
  Clock,
  MapPin,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  ArrowLeft
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

  return (
    <div className="py-10 px-4 sm:px-6 max-w-xl mx-auto">
      {/* Top back navigation & actions */}
      <div className="flex items-center justify-between mb-6">
        <Link to="/" className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Home</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
          <a
            href={getDownloadUrl(`/api/tickets/${ticket.ticket_id}/pdf`)}
            download
            className="festive-button px-4 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF Pass</span>
          </a>
        </div>
      </div>

      {/* Official Concert Ticket Pass (Section 17 Requirement) */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-[#0f0a14] border-2 border-[#d4af37]/50 shadow-[0_20px_50px_rgba(0,0,0,0.8)] overflow-hidden text-slate-100 relative print:border-black print:text-black"
      >
        {/* Pass Header Banner */}
        <div className="bg-gradient-to-b from-[#1f1026] via-[#160a1c] to-[#0f0a14] border-b border-white/[0.08] p-6 sm:p-7 text-center relative">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-[10px] font-black uppercase tracking-[0.25em] px-3 py-1 rounded-full bg-[#d4af37]/15 text-[#f7e8c3] border border-[#d4af37]/35 font-['Cinzel']">
              Heritage Productions Presents
            </span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-[0.06em] uppercase font-['Cinzel'] bg-gradient-to-r from-white via-[#f7e8c3] to-[#d4af37] bg-clip-text text-transparent">
            GARBA NIGHT 2026
          </h1>
          <div className="mt-1 text-xs sm:text-sm font-black uppercase tracking-[0.2em] text-[#d4af37] font-['Cinzel']">
            MYSURU
          </div>
        </div>

        {/* Perforated Stub Line with Left & Right Notches */}
        <div className="relative flex items-center justify-between my-1">
          <div className="w-5 h-10 bg-[#080309] rounded-r-full border-r border-t border-b border-[#d4af37]/50 -ml-1" />
          <div className="flex-1 border-b-2 border-dashed border-[#d4af37]/40 mx-2" />
          <div className="w-5 h-10 bg-[#080309] rounded-l-full border-l border-t border-b border-[#d4af37]/50 -mr-1" />
        </div>

        {/* Ticket Details & QR Code */}
        <div className="p-6 sm:p-8 space-y-6">
          {/* Status Badge */}
          <div className="text-center">
            {isUsed ? (
              <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black bg-[#d4af37]/20 text-[#f3e4b2] border border-[#d4af37]/40 tracking-wider">
                <AlertTriangle className="w-4 h-4 text-[#d4af37]" />
                ALREADY CHECKED IN
              </span>
            ) : isCancelled ? (
              <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black bg-rose-500/20 text-rose-400 border border-rose-500/40 tracking-wider">
                <XCircle className="w-4 h-4" />
                INVALID TICKET (CANCELLED)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-5 py-1.5 rounded-full text-xs sm:text-sm font-black bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 shadow-sm tracking-wider font-['Cinzel']">
                <CheckCircle2 className="w-4 h-4" />
                VALID TICKET • ADMIT ONE
              </span>
            )}
          </div>

          {/* Large QR Code Presentation (High Readability) */}
          <div className="flex flex-col items-center justify-center p-6 rounded-3xl bg-black/60 border border-[#d4af37]/35 shadow-inner">
            {ticket.qr_code_base64 && (
              <div className="p-4 bg-white rounded-2xl shadow-2xl border-2 border-slate-300">
                <img
                  src={ticket.qr_code_base64}
                  alt="Entry QR Code"
                  className="w-52 h-52 sm:w-60 sm:h-60 object-contain"
                />
              </div>
            )}
            <div className="text-xs font-mono text-[#f3e4b2] font-black mt-4 tracking-wider">
              TICKET #{ticket.ticket_id}
            </div>
            <p className="text-[11px] text-slate-400 text-center mt-1">
              Present this high-resolution QR barcode at the Mysuru venue turnstiles.
            </p>
          </div>

          {/* Pass Meta Grid (Customer Name, Booking ID, Ticket Number, Event Date, Venue) */}
          <div className="grid grid-cols-2 gap-3.5 text-xs">
            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider font-['Cinzel']">Customer Name</div>
              <div className="text-sm font-bold text-white mt-0.5 truncate">{ticket.customer_name}</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider font-['Cinzel']">Booking ID</div>
              <div className="text-sm font-bold text-[#f3e4b2] font-mono mt-0.5">{ticket.booking_id}</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider flex items-center gap-1 font-['Cinzel']">
                <Calendar className="w-3 h-3 text-[#d4af37]" /> Event Date
              </div>
              <div className="font-semibold text-white mt-0.5">{config?.event_date || 'October 16, 2026'}</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider flex items-center gap-1 font-['Cinzel']">
                <Clock className="w-3 h-3 text-[#d4af37]" /> Time & Entry
              </div>
              <div className="font-semibold text-white mt-0.5">{config?.event_time || '06:00 PM - 10:00 PM'}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Entry starts 05:30 PM</div>
            </div>

            <div className="col-span-2 p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.08]">
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider flex items-center gap-1 font-['Cinzel']">
                <MapPin className="w-3 h-3 text-[#d4af37]" /> Venue
              </div>
              <div className="font-semibold text-white mt-0.5">
                {config?.venue_name ? `${config.venue_name}, ${config.venue_city || 'Mysuru'}` : 'The Serenity Grove, Mysuru'}
              </div>
            </div>
          </div>

          {/* Security Notice */}
          <div className="p-3.5 rounded-2xl bg-[#d4af37]/10 border border-[#d4af37]/30 text-[11px] text-[#f3e4b2]/90 leading-relaxed flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-[#d4af37] shrink-0 mt-0.5" />
            <div>
              <strong>Single-Entry Policy:</strong> This ticket pass is digitally signed. Duplicate scans or screenshots shared with others will be rejected at the gate. Traditional festive attire encouraged.
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
