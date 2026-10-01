import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Ticket as TicketIcon,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Calendar,
  MapPin,
  AlertCircle,
  CreditCard
} from 'lucide-react';
import { lookupBookingStatus, retryPaymentOrder, verifyPaymentSignature } from '../services/api';
import { Booking } from '../types';
import { useToast } from '../components/Toast';

export const BookingStatusPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryBookingId = searchParams.get('booking_id') || '';

  const [bookingIdInput, setBookingIdInput] = useState(queryBookingId);
  const [contactInput, setContactInput] = useState('');
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(Boolean(queryBookingId));
  const [retrying, setRetrying] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const { error, success, info } = useToast();

  const handleLookup = async (idToSearch: string, contactToSearch?: string) => {
    if (!idToSearch.trim()) {
      error('Input required', 'Please enter your Booking ID.');
      return;
    }

    setLoading(true);
    setErrorMessage('');

    try {
      const data = await lookupBookingStatus(idToSearch.trim(), contactToSearch?.trim());
      setBooking(data);
    } catch (err: any) {
      setBooking(null);
      const detail = err.response?.data?.detail || 'No booking found matching your details. Please check the Booking ID.';
      setErrorMessage(detail);
      error('Not Found', detail);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (queryBookingId) {
      handleLookup(queryBookingId);
    }
  }, [queryBookingId]);

  // Polling if payment is still pending or processing
  useEffect(() => {
    if (!booking) return;

    const isPending =
      booking.booking_status === 'PAYMENT_PENDING' ||
      booking.booking_status === 'PAYMENT_PROCESSING' ||
      booking.payment_status === 'PENDING' ||
      booking.payment_status === 'VERIFICATION_PENDING';

    if (!isPending) return;

    const interval = setInterval(async () => {
      try {
        const updated = await lookupBookingStatus(booking.booking_id, contactInput);
        if (
          updated.booking_status !== booking.booking_status ||
          updated.payment_status !== booking.payment_status
        ) {
          setBooking(updated);
          if (updated.payment_status === 'PAID' || updated.payment_status === 'CAPTURED') {
            success('Payment Confirmed!', 'Your booking is confirmed and digital tickets are ready.');
          }
        }
      } catch {
        // Silent polling failure
      }
    }, 3500);

    return () => clearInterval(interval);
  }, [booking, contactInput]);

  const handleRetryPayment = async () => {
    if (!booking) return;
    try {
      setRetrying(true);
      const order = await retryPaymentOrder(booking.booking_id);

      if (!window.Razorpay) {
        // Dynamically load Razorpay SDK if not yet loaded
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.async = true;
        script.onload = () => openRazorpayModal(order);
        script.onerror = () => {
          setRetrying(false);
          error('Error', 'Could not load Razorpay checkout.');
        };
        document.body.appendChild(script);
      } else {
        openRazorpayModal(order);
      }
    } catch (err: any) {
      setRetrying(false);
      const msg = err.response?.data?.detail || 'Could not re-initialize payment. Please try again.';
      error('Retry Error', msg);
    }
  };

  const openRazorpayModal = (order: any) => {
    const options = {
      key: order.key_id,
      amount: Math.round(order.amount * 100),
      currency: order.currency || 'INR',
      name: 'NAVRANG 2026',
      description: `${order.ticket_count} Official Entry Pass${order.ticket_count > 1 ? 'es' : ''} • Taxes included`,
      order_id: order.razorpay_order_id,
      prefill: {
        name: order.customer_name,
        email: order.customer_email,
        contact: order.customer_phone,
      },
      notes: {
        booking_id: order.booking_id,
        ticket_count: String(order.ticket_count),
      },
      theme: {
        color: '#d4af37',
      },
      handler: async (response: any) => {
        try {
          info('Verifying', 'Verifying payment with gateway...');
          await verifyPaymentSignature({
            booking_id: order.booking_id,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
          success('Success!', 'Payment confirmed.');
          navigate(`/success/${order.booking_id}`);
        } catch (vErr: any) {
          error('Verification Error', 'Payment verification failed. Please check status.');
          handleLookup(order.booking_id);
        } finally {
          setRetrying(false);
        }
      },
      modal: {
        ondismiss: () => {
          setRetrying(false);
          info('Payment Cancelled', 'You can retry payment whenever you are ready.');
        },
      },
    };

    const rzp = new window.Razorpay(options);
    rzp.on('payment.failed', (failRes: any) => {
      setRetrying(false);
      error('Payment Failed', failRes.error?.description || 'Payment was declined. Please retry.');
      handleLookup(order.booking_id);
    });
    rzp.open();
  };

  const isPaid = booking && (booking.payment_status === 'PAID' || booking.payment_status === 'CAPTURED');
  const isFailed = booking && (booking.payment_status === 'FAILED' || booking.booking_status === 'PAYMENT_FAILED');
  const isPending = booking && !isPaid && !isFailed;

  return (
    <div className="min-h-screen py-16 px-4 max-w-4xl mx-auto">
      {/* Page Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold mb-4">
          <ShieldCheck className="w-4 h-4 text-amber-400" />
          <span>Official Event Verification Portal</span>
        </div>
        <h1 className="text-3xl md:text-5xl font-black font-serif text-white tracking-wide mb-3">
          BOOKING & PAYMENT <span className="text-amber-400">STATUS</span>
        </h1>
        <p className="text-slate-400 text-sm max-w-md mx-auto">
          Look up your live reservation, verify bank payment confirmation, and access official encrypted QR entry passes.
        </p>
      </div>

      {/* Search / Lookup Form */}
      <div className="glass-panel p-6 md:p-8 rounded-3xl border border-white/10 shadow-2xl mb-8">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleLookup(bookingIdInput, contactInput);
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Booking Reference ID *
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="e.g. GN-2026-48291"
                  value={bookingIdInput}
                  onChange={(e) => setBookingIdInput(e.target.value)}
                  className="w-full px-4 py-3.5 rounded-2xl bg-black/50 border border-white/10 text-white placeholder-slate-500 font-mono text-sm focus:outline-none focus:border-amber-400 uppercase"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Registered Mobile or Email (Optional)
              </label>
              <input
                type="text"
                placeholder="Phone (10 digits) or Email address"
                value={contactInput}
                onChange={(e) => setContactInput(e.target.value)}
                className="w-full px-4 py-3.5 rounded-2xl bg-black/50 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-amber-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600 text-slate-950 font-black text-sm uppercase tracking-wider hover:opacity-95 transition-all shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                <span>Checking Live Records...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Lookup Booking Status</span>
              </>
            )}
          </button>
        </form>

        {errorMessage && (
          <div className="mt-4 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {/* Booking Details Card when found */}
      {booking && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel rounded-3xl border border-white/10 overflow-hidden shadow-2xl"
        >
          {/* Status Header Banner */}
          <div
            className={`p-6 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              isPaid
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : isFailed
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            }`}
          >
            <div className="flex items-center gap-3">
              {isPaid ? (
                <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />
              ) : isFailed ? (
                <XCircle className="w-8 h-8 text-rose-400 shrink-0" />
              ) : (
                <Clock className="w-8 h-8 text-amber-400 animate-spin shrink-0" />
              )}
              <div>
                <span className="text-[10px] uppercase font-bold tracking-widest block opacity-75">
                  Live Payment Status
                </span>
                <h2 className="text-xl font-black font-serif uppercase tracking-wide">
                  {isPaid
                    ? '✓ Payment Successful • Booking Confirmed'
                    : isFailed
                    ? '✕ Payment Failed / Declined'
                    : 'Payment Processing • Verifying Transaction'}
                </h2>
              </div>
            </div>

            <div className="text-right sm:border-l sm:border-white/10 sm:pl-4">
              <span className="text-[10px] text-slate-400 uppercase tracking-widest block">
                Booking Reference
              </span>
              <span className="text-sm font-mono font-bold text-white uppercase">
                {booking.booking_id}
              </span>
            </div>
          </div>

          {/* Details Body */}
          <div className="p-6 md:p-8 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                  Customer
                </span>
                <span className="text-sm font-bold text-white block truncate">
                  {booking.customer_name}
                </span>
                <span className="text-xs text-slate-400 font-mono block truncate">
                  {booking.phone}
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                  Entry Passes
                </span>
                <span className="text-sm font-bold text-white flex items-center gap-1.5">
                  <TicketIcon className="w-4 h-4 text-amber-400" />
                  <span>{booking.ticket_count} {booking.ticket_count > 1 ? 'Tickets' : 'Ticket'}</span>
                </span>
                {(booking.group_discount ?? 0) > 0 && (
                  <span className="text-[10px] text-amber-400 font-semibold block">
                    Group Offer (1 Free Pass)
                  </span>
                )}
              </div>

              <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                  Total Amount
                </span>
                <span className="text-lg font-black font-mono text-emerald-400">
                  ₹{booking.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-400 block">Taxes included</span>
              </div>

              <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                  Payment Gateway
                </span>
                <span className="text-sm font-bold text-amber-300 font-mono block">
                  {booking.payment_method || 'RAZORPAY'}
                </span>
                {booking.razorpay_payment_id && (
                  <span className="text-[10px] text-slate-400 font-mono block truncate" title={booking.razorpay_payment_id}>
                    {booking.razorpay_payment_id}
                  </span>
                )}
              </div>
            </div>

            {/* Event Details snippet */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300 bg-black/40 p-4 rounded-2xl border border-white/5">
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-amber-400" />
                <span>October 17, 2026 • 06:30 PM - 10:00 PM</span>
              </div>
              <div className="flex items-center gap-1.5">
                <MapPin className="w-4 h-4 text-amber-400" />
                <span>The Green Acres, Mysuru</span>
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
              {isPaid ? (
                <>
                  <p className="text-xs text-slate-400">
                    Your payment was verified. Present your digital QR passes at the entrance gate.
                  </p>
                  <Link
                    to={`/success/${booking.booking_id}`}
                    className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20"
                  >
                    <TicketIcon className="w-4 h-4" />
                    <span>View & Download QR Passes</span>
                  </Link>
                </>
              ) : isFailed ? (
                <>
                  <p className="text-xs text-rose-300">
                    Your previous payment attempt was declined or incomplete. You can retry payment now to confirm your booking.
                  </p>
                  <button
                    onClick={handleRetryPayment}
                    disabled={retrying}
                    className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:opacity-95 text-slate-950 font-black text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 cursor-pointer disabled:opacity-50"
                  >
                    {retrying ? (
                      <>
                        <div className="w-4 h-4 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                        <span>Opening Razorpay...</span>
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4" />
                        <span>Try Payment Again</span>
                      </>
                    )}
                  </button>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2 text-xs text-amber-300">
                    <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                    <span>Waiting for bank confirmation callback or webhook...</span>
                  </div>
                  <button
                    onClick={() => handleLookup(booking.booking_id, contactInput)}
                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Refresh Now</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default BookingStatusPage;
