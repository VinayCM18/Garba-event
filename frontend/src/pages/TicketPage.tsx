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

      {/* Official Concert Ticket Pass Matching Uploaded Design */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden text-slate-800 relative print:border-black print:text-black"
      >
        {/* Pass Header Banner - Deep Indigo/Navy #1C1949 */}
        <div className="bg-[#1C1949] p-6 sm:p-7 text-center relative text-white">
          <h1 className="text-2xl sm:text-3xl font-black tracking-wider uppercase text-[#EA580C] font-['Cinzel'] flex items-center justify-center gap-2">
            <span>❖</span>
            <span>{config?.event_name || 'NAVRANG 2026'}</span>
            <span>❖</span>
          </h1>

          <div className="mt-1 text-[11px] sm:text-xs font-bold uppercase tracking-widest text-[#FBBF24]">
            IN COLLABORATION WITH THE HAPPY CIRCLE
          </div>

          <div className="mt-1 text-xs italic text-[#FCD34D] font-serif">
            {config?.event_tagline || 'Celebrate. Dance. Connect.'}
          </div>

          <div className="mt-3 text-xs sm:text-sm font-extrabold tracking-wider uppercase text-white">
            OFFICIAL ENTRY PASS — PASS 1 OF 1
          </div>
        </div>

        {/* 4-Column Ticket Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 bg-white border-b border-slate-200 text-left text-xs divide-x divide-y sm:divide-y-0 divide-slate-200">
          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">ATTENDEE NAME</div>
            <div className="text-sm font-bold text-slate-900 mt-1 truncate">{ticket.customer_name}</div>
          </div>

          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">BOOKING ID</div>
            <div className="text-sm font-bold text-slate-900 mt-1 font-mono">{ticket.booking_id}</div>
          </div>

          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">TICKET NUMBER</div>
            <div className="text-sm font-bold text-slate-900 mt-1 font-mono truncate">{ticket.ticket_id}</div>
          </div>

          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">PASS ORDER</div>
            <div className="text-sm font-bold text-slate-900 mt-1">Pass 1 of 1</div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 bg-white border-b border-slate-200 text-left text-xs divide-x divide-y sm:divide-y-0 divide-slate-200">
          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">EVENT DATE & TIME</div>
            <div className="text-xs font-semibold text-slate-800 mt-1">
              <div>{config?.event_date || 'October 17, 2026'}</div>
              <div className="text-slate-500">{config?.event_time || '06:30 PM - 10:00 PM'}</div>
            </div>
          </div>

          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">VENUE LOCATION</div>
            <div className="text-xs font-semibold text-slate-800 mt-1">
              <div className="font-bold">{config?.venue_name || 'Green Acres'}</div>
              <div className="text-slate-500 text-[11px] truncate">{config?.venue_address || 'Green Acres, Mysuru'}, {config?.venue_city || 'Mysuru'}</div>
            </div>
          </div>

          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">PAYMENT STATUS</div>
            <div className="text-sm font-bold text-slate-900 mt-1 flex items-center gap-1">
              <span>✓ PAID (₹{Math.round(ticket.ticket_price || config?.ticket_price || 599)})</span>
            </div>
          </div>

          <div className="p-3 sm:p-3.5">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">TICKET STATUS</div>
            <div className="text-sm font-bold mt-1 flex items-center gap-1.5">
              {isUsed ? (
                <span className="text-amber-600 font-bold">● CHECKED IN</span>
              ) : isCancelled ? (
                <span className="text-rose-600 font-bold">● CANCELLED</span>
              ) : (
                <span className="text-slate-900 font-bold">● VALID</span>
              )}
            </div>
          </div>
        </div>

        {/* QR Code Presentation */}
        <div className="p-6 bg-slate-50 border-b border-slate-200 text-center flex flex-col items-center justify-center">
          {ticket.qr_code_base64 && (
            <div className="p-3 bg-white rounded-xl shadow-md border border-slate-300 inline-block">
              <img
                src={ticket.qr_code_base64.startsWith('data:') ? ticket.qr_code_base64 : `data:image/png;base64,${ticket.qr_code_base64}`}
                alt="Entry QR Code"
                className="w-48 h-48 sm:w-56 sm:h-56 object-contain"
              />
            </div>
          )}
          <p className="text-xs text-slate-500 mt-2 font-medium">
            Scan this barcode at security turnstiles for gate admission
          </p>
        </div>

        {/* Important Venue Instructions Box - Cream #FFFDF5, Amber border #FDE68A */}
        <div className="m-4 sm:m-6 p-4 rounded-xl bg-[#FFFDF5] border border-[#FDE68A] text-left">
          <div className="text-xs font-bold text-[#B45309] uppercase tracking-wider mb-2">
            IMPORTANT VENUE INSTRUCTIONS
          </div>
          <ul className="text-xs text-slate-700 space-y-1.5 list-disc list-inside">
            <li>Gates open promptly at 06:30 PM. Show this barcode or digital pass at turnstiles.</li>
            <li>Event Timings: 06:30 PM onwards till 10:00 PM. Gates close at 10:00 PM.</li>
            <li>Entry will be granted only after successful QR scanning at security.</li>
            <li>Each QR code is uniquely encrypted and admits exactly one person once.</li>
            <li>Traditional festive attire is celebrated and recommended.</li>
            <li>Carry valid Government photo ID matching the attendee name.</li>
          </ul>
        </div>

        {/* Footer info line */}
        <div className="pb-4 text-center text-[11px] text-slate-400">
          Pass 1 of 1 • Booking #{ticket.booking_id} • {config?.event_name || 'NAVRANG 2026'} × THE HAPPY CIRCLE Official E-Ticket
        </div>
      </motion.div>
    </div>
  );
};
