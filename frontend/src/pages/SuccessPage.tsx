import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import confetti from 'canvas-confetti';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  Ticket as TicketIcon,
  Download,
  Mail,
  Home,
  QrCode,
  Calendar,
  MapPin,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  Share2,
  Copy,
  Check,
  Clock,
  RefreshCw,
  XCircle,
  FileCheck2,
  CreditCard
} from 'lucide-react';
import { fetchBookingDetails, resendCustomerBookingEmail } from '../services/api';
import { Booking } from '../types';
import { useToast } from '../components/Toast';
import { ManualUpiPaymentModal } from '../components/ManualUpiPaymentModal';

export const SuccessPage: React.FC = () => {
  const { bookingId } = useParams<{ bookingId: string }>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [copiedShare, setCopiedShare] = useState(false);
  const [retryModalOpen, setRetryModalOpen] = useState(false);
  const [emailingTicket, setEmailingTicket] = useState(false);
  const { error, success, info } = useToast();

  const handleEmailTicket = async () => {
    if (!booking) return;
    try {
      setEmailingTicket(true);
      const res = await resendCustomerBookingEmail(booking.booking_id);
      success('Ticket Emailed', res.message || `Passes dispatched to ${booking.email}`);
    } catch (err: any) {
      error('Email Error', err.response?.data?.detail || 'Could not send email. Please download the PDF ticket instead.');
    } finally {
      setEmailingTicket(false);
    }
  };

  const loadBooking = async (silent = false) => {
    if (!bookingId) return;
    if (!silent) setLoading(true);
    else setRefreshing(true);

    try {
      const data = await fetchBookingDetails(bookingId);
      setBooking(data);
      if (!silent) setLoading(false);
      setRefreshing(false);
    } catch (err) {
      console.error('Failed to load booking:', err);
      if (!silent) {
        setLoading(false);
        error('Not Found', 'Could not locate details for this booking ID.');
      }
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadBooking();
  }, [bookingId]);

  // Real-time polling when booking is under manual verification
  useEffect(() => {
    if (!booking) return;
    const isPending =
      booking.booking_status === 'PAYMENT_VERIFICATION_PENDING' ||
      booking.payment_status === 'VERIFICATION_PENDING';

    if (isPending) {
      const interval = setInterval(() => {
        loadBooking(true);
      }, 7000);
      return () => clearInterval(interval);
    }
  }, [booking?.booking_status, booking?.payment_status]);

  // Celebration confetti only when CONFIRMED
  useEffect(() => {
    if (booking && booking.booking_status === 'CONFIRMED' && booking.payment_status === 'PAID') {
      try {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#d4af37', '#f3e4b2', '#10b981', '#ffffff', '#cbd5e1'],
        });
      } catch (e) {
        // ignore
      }
    }
  }, [booking?.booking_status, booking?.payment_status]);

  const handleCopyShareLink = () => {
    if (typeof window !== 'undefined') {
      const shareUrl = `${window.location.origin}/book?count=10`;
      navigator.clipboard.writeText(shareUrl);
      setCopiedShare(true);
      setTimeout(() => setCopiedShare(false), 2500);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-12 h-12 border-3 border-[#d4af37]/30 border-t-[#d4af37] rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-400">Loading booking status...</p>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="py-24 px-4 text-center max-w-md mx-auto">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Booking Not Found</h2>
        <p className="text-sm text-slate-400 mb-6">
          We could not find booking reference #{bookingId}. Please check the URL or check your email.
        </p>
        <Link to="/" className="festive-button px-6 py-2.5 rounded-full text-xs font-bold inline-block">
          Return to Home
        </Link>
      </div>
    );
  }

  const isPendingVerification =
    booking.booking_status === 'PAYMENT_VERIFICATION_PENDING' ||
    booking.payment_status === 'VERIFICATION_PENDING';

  const isPaymentPending =
    booking.booking_status === 'PAYMENT_PENDING' ||
    (booking.payment_status === 'PENDING' && !booking.utr_number);

  const isPaymentFailedOrRejected =
    booking.payment_status === 'REJECTED' ||
    booking.booking_status === 'PAYMENT_FAILED';

  const isConfirmed =
    booking.booking_status === 'CONFIRMED' && booking.payment_status === 'PAID';

  const isGroupOffer = Boolean(
    (booking.group_discount && booking.group_discount > 0) ||
    booking.is_group_offer ||
    booking.ticket_count === 10
  );
  const ticketPrice = booking.ticket_price || 599;
  const regularValue = booking.regular_amount || (ticketPrice * booking.ticket_count);
  const savings = booking.group_discount || (isGroupOffer ? ticketPrice : 0);
  const ticketSubtotal = booking.ticket_subtotal || (regularValue - savings);

  return (
    <div className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
      {/* Modal for retry if rejected or pending */}
      <ManualUpiPaymentModal
        isOpen={retryModalOpen}
        bookingId={booking.booking_id}
        amount={booking.amount}
        customerName={booking.customer_name}
        onSuccess={() => {
          setRetryModalOpen(false);
          loadBooking();
        }}
        onDismiss={() => setRetryModalOpen(false)}
      />

      {/* ========================================================================= */}
      {/* STATE 1: PAYMENT SUBMITTED / VERIFICATION PENDING (Section 15)            */}
      {/* ========================================================================= */}
      {isPendingVerification && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-8"
        >
          {/* Status Header */}
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center mx-auto mb-4 shadow-xl shadow-amber-500/10 relative">
              <Clock className="w-8 h-8 animate-pulse" />
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-400 animate-ping opacity-75" />
            </div>

            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-black uppercase tracking-wider mb-3">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span>Status: VERIFICATION PENDING</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-black text-white font-['Cinzel'] tracking-wide">
              PAYMENT SUBMITTED
            </h1>
            <p className="mt-3 text-base text-[#f3e4b2] max-w-xl mx-auto font-medium leading-relaxed">
              Your payment is being verified. Your booking will be confirmed after review.
            </p>
          </div>

          {/* Details Card */}
          <div className="glass-panel-gold rounded-3xl p-6 sm:p-8 border border-[#d4af37]/35 shadow-2xl">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center pb-6 border-b border-white/[0.08]">
              <div>
                <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider font-['Cinzel']">
                  BOOKING ID
                </div>
                <div className="text-2xl font-black text-[#f3e4b2] font-mono mt-1">
                  {booking.booking_id}
                </div>
              </div>

              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold tracking-wider">
                  Amount
                </div>
                <div className="text-xl font-black text-white font-mono mt-1">
                  ₹{booking.amount.toLocaleString('en-IN')}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {booking.ticket_count} Admission Pass{booking.ticket_count > 1 ? 'es' : ''}
                </div>
              </div>

              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold tracking-wider">
                  UTR / Reference ID
                </div>
                <div className="text-xl font-black text-amber-400 font-mono mt-1 break-all">
                  {booking.utr_number || 'Under Submission'}
                </div>
              </div>
            </div>

            {/* Verification Steps Visual */}
            <div className="mt-8 space-y-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Verification Steps
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-bold text-white">1. Details Received</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">UTR reference recorded</div>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/40 flex items-start gap-3">
                  <Clock className="w-5 h-5 text-amber-400 shrink-0 mt-0.5 animate-spin" style={{ animationDuration: '4s' }} />
                  <div>
                    <div className="text-xs font-bold text-amber-300">2. Admin Verification</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Matching bank credit</div>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.08] flex items-start gap-3 opacity-60">
                  <TicketIcon className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-bold text-slate-300">3. Pass Generation</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Dispatched to email</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Real-time sync note */}
            <div className="mt-6 p-4 rounded-2xl bg-black/40 border border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-300">
              <div className="flex items-center gap-2">
                <RefreshCw className={`w-4 h-4 text-[#d4af37] ${refreshing ? 'animate-spin' : ''}`} />
                <span>
                  Our organizers are verifying accounts. This screen refreshes automatically.
                </span>
              </div>
              <button
                onClick={() => loadBooking(true)}
                disabled={refreshing}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white font-bold text-xs flex items-center gap-1.5 transition-all shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                <span>Refresh Now</span>
              </button>
            </div>

            <div className="mt-8 flex justify-center gap-3">
              <Link
                to="/"
                className="luxury-outline-button px-7 py-3 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                <span>Return to Home</span>
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      {/* ========================================================================= */}
      {/* STATE 2: PAYMENT REJECTED / FAILED                                       */}
      {/* ========================================================================= */}
      {isPaymentFailedOrRejected && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-8"
        >
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center justify-center mx-auto mb-4 shadow-xl shadow-rose-500/10">
              <XCircle className="w-9 h-9" />
            </div>
            <h1 className="text-3xl sm:text-5xl font-black text-white font-['Outfit'] uppercase">
              Payment Rejected
            </h1>
            <p className="mt-2 text-base text-rose-300 font-medium">
              We could not verify the submitted payment transaction.
            </p>
          </div>

          <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-rose-500/30 shadow-2xl">
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/25 mb-6">
              <div className="text-xs font-bold uppercase tracking-wider text-rose-400 mb-1">
                Reason for Rejection:
              </div>
              <div className="text-sm font-semibold text-white">
                {booking.rejection_reason || 'UTR / Transaction Reference was not found in our bank records.'}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-center pb-6 border-b border-white/[0.08]">
              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold">Booking ID</div>
                <div className="text-base font-mono font-bold text-white mt-1">{booking.booking_id}</div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold">Amount Due</div>
                <div className="text-base font-mono font-bold text-white mt-1">₹{booking.amount.toLocaleString('en-IN')}</div>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
              <button
                onClick={() => setRetryModalOpen(true)}
                className="festive-button px-7 py-3.5 rounded-full text-xs font-black uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-[#d4af37]/25"
              >
                <span>RETRY PAYMENT SUBMISSION</span>
              </button>

              <Link
                to="/"
                className="luxury-outline-button px-7 py-3.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                <span>Return to Home</span>
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      {/* ========================================================================= */}
      {/* STATE 3: PAYMENT PENDING (Not yet submitted UTR)                           */}
      {/* ========================================================================= */}
      {isPaymentPending && !isPendingVerification && !isPaymentFailedOrRejected && !isConfirmed && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-8"
        >
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center mx-auto mb-4">
              <CreditCard className="w-9 h-9" />
            </div>
            <h1 className="text-3xl sm:text-5xl font-black text-white font-['Outfit'] uppercase">
              Payment Pending
            </h1>
            <p className="mt-2 text-base text-slate-400 font-medium">
              Please complete your UPI payment and submit the transaction reference.
            </p>
          </div>

          <div className="glass-panel-gold rounded-3xl p-6 sm:p-8 border border-[#d4af37]/30 text-center">
            <div className="text-2xl font-black text-white font-mono mb-2">
              ₹{booking.amount.toLocaleString('en-IN')}
            </div>
            <p className="text-xs text-slate-300 mb-6">
              Booking Ref: <strong className="text-[#f3e4b2] font-mono">{booking.booking_id}</strong>
            </p>

            <button
              onClick={() => setRetryModalOpen(true)}
              className="festive-button px-8 py-3.5 rounded-full text-xs font-black uppercase tracking-wider inline-flex items-center gap-2 shadow-lg shadow-[#d4af37]/30"
            >
              <span>SCAN QR & SUBMIT PAYMENT</span>
            </button>
          </div>
        </motion.div>
      )}

      {/* ========================================================================= */}
      {/* STATE 4: BOOKING CONFIRMED (Admin has approved payment)                   */}
      {/* ========================================================================= */}
      {isConfirmed && (
        <>
          {/* Celebration Header (Section 16 Requirement) */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center mb-10"
          >
            <div className="w-16 h-16 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4 shadow-xl shadow-emerald-500/20 text-2xl font-black">
              ✓
            </div>
            <h1 className="text-3xl sm:text-5xl font-black text-white font-['Cinzel'] tracking-wide">
              BOOKING CONFIRMED
            </h1>
            <p className="mt-2 text-base sm:text-lg text-[#f3e4b2] font-semibold">
              You're all set for Garba Night 2026.
            </p>
            <div className="mt-3 inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-slate-300">
              <span className="text-slate-400 font-bold uppercase font-['Cinzel']">BOOKING ID:</span>
              <span className="text-[#d4af37] font-black">{booking.booking_id}</span>
            </div>
          </motion.div>

          {/* Group Offer Celebration Banner */}
          {isGroupOffer && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8 p-6 sm:p-8 rounded-3xl glass-panel-gold border-2 border-[#d4af37] shadow-[0_0_35px_rgba(212,175,55,0.3)] relative overflow-hidden text-center"
            >
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs font-black uppercase tracking-wider mb-3">
                🎉 GROUP OFFER UNLOCKED!
              </div>
              <h2 className="text-2xl sm:text-4xl font-black text-white uppercase font-['Outfit']">
                BUY 10, PAY FOR 9
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-slate-300">
                Congratulations! You qualified for the group promotion.
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-6 text-center">
                <div className="p-3 rounded-2xl bg-black/40 border border-white/10">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">You Received</div>
                  <div className="text-lg font-black text-white mt-1">10 Tickets</div>
                </div>
                <div className="p-3 rounded-2xl bg-black/40 border border-white/10">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">You Paid For</div>
                  <div className="text-lg font-black text-[#f3e4b2] mt-1">9 Tickets</div>
                </div>
                <div className="p-3 rounded-2xl bg-black/40 border border-white/10">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">You Saved</div>
                  <div className="text-lg font-black text-emerald-400 mt-1">₹{savings.toLocaleString('en-IN')}</div>
                </div>
                <div className="p-3 rounded-2xl bg-black/40 border border-white/10">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Regular Value</div>
                  <div className="text-lg font-bold font-mono text-slate-400 line-through mt-1">₹{regularValue.toLocaleString('en-IN')}</div>
                </div>
                <div className="p-3 rounded-2xl bg-black/40 border border-white/10 col-span-2 sm:col-span-1">
                  <div className="text-[10px] text-[#d4af37] uppercase font-bold">Ticket Amount</div>
                  <div className="text-lg font-black font-mono text-white mt-1">₹{ticketSubtotal.toLocaleString('en-IN')}</div>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                <a
                  href={`/api/bookings/${booking.booking_id}/pdf`}
                  download
                  className="festive-button px-7 py-3 rounded-full text-xs font-black uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-[#d4af37]/20"
                >
                  <Download className="w-4 h-4" />
                  <span>DOWNLOAD ALL TICKETS</span>
                </a>

                {booking.tickets[0]?.qr_token_raw && (
                  <a
                    href="#ticket-list"
                    className="luxury-outline-button px-7 py-3 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2"
                  >
                    <QrCode className="w-4 h-4 text-[#d4af37]" />
                    <span>VIEW TICKETS</span>
                  </a>
                )}
              </div>
            </motion.div>
          )}

          {/* Confirmation Summary Card */}
          <div className="glass-panel-gold rounded-3xl p-6 sm:p-8 border border-[#d4af37]/30 shadow-2xl mb-8">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center pb-6 border-b border-white/[0.08]">
              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold tracking-wider">Booking ID</div>
                <div className="text-base sm:text-lg font-black text-[#f3e4b2] font-mono mt-1">
                  {booking.booking_id}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold tracking-wider">Total Passes</div>
                <div className="text-base sm:text-lg font-black text-white font-mono mt-1">
                  {booking.ticket_count} Admit Pass{booking.ticket_count > 1 ? 'es' : ''}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold tracking-wider">Amount Paid</div>
                <div className="text-base sm:text-lg font-black text-emerald-400 font-mono mt-1">
                  ₹{booking.amount.toLocaleString('en-IN')}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-400 uppercase font-bold tracking-wider">Payment Status</div>
                <div className="mt-1">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    ✓ {booking.payment_status}
                  </span>
                </div>
              </div>
            </div>

            {/* Email Notice */}
            <div className="mt-5 flex items-start gap-3 p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-300">
              <Mail className="w-4 h-4 text-[#d4af37] shrink-0 mt-0.5" />
              <div>
                Official confirmation email with entry QR passes and attached printable PDF tickets has been dispatched to{' '}
                <strong className="text-white">{booking.email}</strong>.
              </div>
            </div>

            {/* Global Action Buttons (Section 16 Requirement) */}
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3.5">
              <a
                href="#ticket-list"
                className="festive-button px-6 py-3.5 rounded-full text-xs font-black uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-[#d4af37]/20 touch-target cursor-pointer"
              >
                <QrCode className="w-4 h-4" />
                <span>VIEW TICKET</span>
              </a>

              <a
                href={`/api/bookings/${booking.booking_id}/pdf`}
                download
                className="luxury-outline-button px-6 py-3.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2 touch-target cursor-pointer"
              >
                <Download className="w-4 h-4 text-[#d4af37]" />
                <span>DOWNLOAD TICKET</span>
              </a>

              <button
                type="button"
                onClick={handleEmailTicket}
                disabled={emailingTicket}
                className="luxury-outline-button px-6 py-3.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2 touch-target cursor-pointer disabled:opacity-50"
              >
                <Mail className="w-4 h-4 text-[#d4af37]" />
                <span>{emailingTicket ? 'SENDING EMAIL...' : 'EMAIL TICKET'}</span>
              </button>

              <Link
                to="/"
                className="px-5 py-3.5 rounded-full text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-white transition-colors flex items-center gap-1.5 touch-target"
              >
                <Home className="w-3.5 h-3.5" />
                <span>Home</span>
              </Link>
            </div>
          </div>

          {/* Individual Ticket Cards */}
          <div id="ticket-list" className="space-y-4 mb-10">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white font-['Outfit'] flex items-center gap-2">
                <TicketIcon className="w-5 h-5 text-[#d4af37]" />
                Your Admission Tickets ({booking.tickets.length})
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {booking.tickets.map((ticket, idx) => (
                <div
                  key={ticket.ticket_id}
                  className="p-5 rounded-2xl glass-panel border border-white/[0.08] flex items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-[#d4af37]/20 text-[#f3e4b2]">
                      Ticket {String(idx + 1).padStart(2, '0')} {idx === 9 && isGroupOffer ? '• (FREE BONUS)' : ''}
                    </span>
                    <div className="text-sm font-black font-mono text-white mt-1">
                      {ticket.ticket_id}
                    </div>
                    <div className="text-xs text-slate-400">
                      {ticket.customer_name}
                    </div>
                  </div>

                  {ticket.qr_code_base64 && (
                    <div className="p-2 bg-white rounded-xl shadow-md shrink-0">
                      <img
                        src={`data:image/png;base64,${ticket.qr_code_base64}`}
                        alt={ticket.ticket_id}
                        className="w-16 h-16 object-contain"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Social Sharing Card */}
          <div className="mb-10 p-6 sm:p-8 rounded-3xl glass-panel border border-white/[0.08] text-center">
            <div className="inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-[#d4af37] mb-2">
              <span>COMING WITH YOUR FRIENDS?</span>
            </div>
            <h3 className="text-xl sm:text-2xl font-black text-white uppercase font-['Outfit']">
              BUY 10, PAY FOR 9
            </h3>
            <p className="mt-1 text-xs text-slate-300 max-w-md mx-auto">
              Share the Garba Night 2026 group promotion with your friends and family so they also get a free ticket!
            </p>
            <div className="mt-5 flex justify-center">
              <button
                onClick={handleCopyShareLink}
                className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/15 text-[#f3e4b2] text-xs font-bold flex items-center gap-2 border border-white/15 transition-all"
              >
                {copiedShare ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">Copied Group Offer Link!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>Copy Group Booking Link</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
