import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import confetti from 'canvas-confetti';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Ticket,
  User,
  Mail,
  Phone,
  Lock,
  ArrowRight,
  AlertCircle,
  Sparkles,
  Minus,
  Plus,
  CreditCard,
  Receipt,
  Flame,
  CheckCircle2,
  Gift
} from 'lucide-react';
import {
  fetchPublicConfig,
  createPaymentOrder,
  verifyPaymentSignature,
  failPaymentOrder,
  calculatePaymentFee,
  FeeCalculation
} from '../services/api';
import { EventConfig } from '../types';
import { useToast } from '../components/Toast';
import { RazorpayModalSimulator } from '../components/RazorpayModalSimulator';
import { ManualUpiPaymentModal } from '../components/ManualUpiPaymentModal';

const bookingSchema = z.object({
  customer_name: z.string().min(2, 'Please enter your full name (minimum 2 characters)'),
  email: z.string().email('Please enter a valid email address'),
  phone: z
    .string()
    .regex(/^(?:\+91|91)?[6-9]\d{9}$/, 'Please enter a valid 10-digit Indian phone number (starting 6-9)'),
  ticket_count: z.number().min(1, 'Minimum 1 ticket required').max(10, 'Maximum 10 tickets per booking'),
});

type BookingFormData = z.infer<typeof bookingSchema>;

declare global {
  interface Window {
    Razorpay: any;
  }
}

export const BookingPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { error, success, info } = useToast();

  const [config, setConfig] = useState<EventConfig | null>(null);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadingStatusText, setLoadingStatusText] = useState('Initializing order...');
  const [pricing, setPricing] = useState<FeeCalculation | null>(null);
  const [calculatingFee, setCalculatingFee] = useState(false);

  // Modal states
  const [simulatorOpen, setSimulatorOpen] = useState(false);
  const [upiModalOpen, setUpiModalOpen] = useState(false);
  const [currentOrder, setCurrentOrder] = useState<any>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors }
  } = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
    defaultValues: {
      customer_name: '',
      email: '',
      phone: '',
      ticket_count: 2,
    },
  });

  const ticketCount = watch('ticket_count') || 1;

  // Handle URL query parameter for count (e.g. /book?count=10)
  useEffect(() => {
    const countParam = searchParams.get('count');
    if (countParam) {
      const parsed = parseInt(countParam, 10);
      if (!isNaN(parsed) && parsed >= 1 && parsed <= 10) {
        setValue('ticket_count', parsed, { shouldValidate: true });
      }
    }
  }, [searchParams, setValue]);

  // Trigger small celebratory confetti when selecting exactly 10 tickets
  const prevCountRef = useRef(ticketCount);
  useEffect(() => {
    if (ticketCount === 10 && prevCountRef.current !== 10) {
      try {
        confetti({
          particleCount: 45,
          spread: 60,
          origin: { y: 0.6 },
          colors: ['#d4af37', '#f3e4b2', '#10b981', '#ffffff']
        });
      } catch (e) {
        // canvas-confetti fallback
      }
    }
    prevCountRef.current = ticketCount;
  }, [ticketCount]);

  // Load public event configuration
  useEffect(() => {
    fetchPublicConfig()
      .then((cfg) => {
        setConfig(cfg);
        setLoadingConfig(false);
      })
      .catch((err) => {
        console.error('Failed to load event config:', err);
        setLoadingConfig(false);
      });
  }, []);

  // Fetch exact backend fee calculation whenever ticket count changes
  useEffect(() => {
    let isCurrent = true;
    setCalculatingFee(true);
    calculatePaymentFee(ticketCount)
      .then((res) => {
        if (isCurrent) {
          setPricing(res);
          setCalculatingFee(false);
        }
      })
      .catch((err) => {
        console.error('Error calculating payment fee:', err);
        if (isCurrent) setCalculatingFee(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [ticketCount]);

  const ticketPrice = pricing?.ticket_price || config?.ticket_price || 599;
  const isGroupOffer = pricing?.is_group_offer ?? (ticketCount === 10);
  const regularPrice = pricing?.regular_amount ?? (ticketPrice * ticketCount);
  const groupDiscount = pricing?.group_discount ?? (isGroupOffer ? ticketPrice : 0);
  const ticketSubtotal = pricing?.ticket_subtotal ?? (regularPrice - groupDiscount);
  const paymentFee = pricing?.payment_fee ?? Math.round(ticketSubtotal * 0.02 * 100) / 100;
  const gstAmount = pricing?.gst_amount ?? Math.round(paymentFee * 0.18 * 100) / 100;
  const totalPayable = pricing?.total_amount ?? Math.round((ticketSubtotal + paymentFee + gstAmount) * 100) / 100;

  const handleStepTickets = (delta: number) => {
    const current = ticketCount || 1;
    const next = Math.max(1, Math.min(10, current + delta));
    setValue('ticket_count', next, { shouldValidate: true });
  };

  const onSubmit = async (data: BookingFormData) => {
    try {
      setSubmitting(true);
      setLoadingStatusText('Reserving inventory & generating payment order...');

      // Generate idempotency key for this click
      const idempotencyKey = `order_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

      const orderResponse = await createPaymentOrder({
        customer_name: data.customer_name,
        email: data.email,
        phone: data.phone,
        ticket_count: data.ticket_count,
        idempotency_key: idempotencyKey,
      });

      setCurrentOrder(orderResponse);
      setSubmitting(false);

      // Real Razorpay Live/Test Checkout Flow
      const launchRazorpay = () => {
        const options = {
          key: orderResponse.key_id,
          amount: Math.round(orderResponse.amount * 100),
          currency: orderResponse.currency || 'INR',
          name: config?.event_name || 'GARBA NIGHT 2026',
          description: `${data.ticket_count} Official Entry Pass${data.ticket_count > 1 ? 'es' : ''} • Taxes included`,
          order_id: orderResponse.razorpay_order_id,
          prefill: {
            name: data.customer_name,
            email: data.email,
            contact: data.phone,
          },
          notes: {
            booking_id: orderResponse.booking_id,
            ticket_count: String(data.ticket_count),
          },
          theme: {
            color: '#d4af37',
          },
          handler: async (response: any) => {
            await handlePaymentVerification(
              orderResponse.booking_id,
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            );
          },
          modal: {
            ondismiss: () => {
              setSubmitting(false);
              info('Payment cancelled', 'You can retry payment whenever you are ready.');
            },
          },
        };

        const rzp = new window.Razorpay(options);
        rzp.on('payment.failed', async (failRes: any) => {
          setSubmitting(false);
          const reason = failRes.error?.description || 'Payment was declined or cancelled.';
          try {
            await failPaymentOrder(orderResponse.booking_id, reason);
          } catch {
            // silent catch
          }
          error(
            'Payment Failed',
            reason + ' Your booking has not been confirmed. Please retry.'
          );
          navigate(`/success/${orderResponse.booking_id}`);
        });
        rzp.open();
      };

      if (!window.Razorpay) {
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.async = true;
        script.onload = () => launchRazorpay();
        script.onerror = () => {
          setSubmitting(false);
          error('Gateway Error', 'Could not load Razorpay checkout SDK. Please check your internet connection.');
        };
        document.body.appendChild(script);
      } else {
        launchRazorpay();
      }
    } catch (err: any) {
      setSubmitting(false);
      const msg = err.response?.data?.detail || 'Failed to initialize booking order. Please check inputs.';
      error('Booking Error', msg);
    }
  };

  const handlePaymentVerification = async (
    bookingId: string,
    orderId: string,
    paymentId: string,
    signature: string
  ) => {
    try {
      setSubmitting(true);
      setLoadingStatusText('Verifying bank signature & issuing encrypted QR passes...');

      await verifyPaymentSignature({
        booking_id: bookingId,
        razorpay_order_id: orderId,
        razorpay_payment_id: paymentId,
        razorpay_signature: signature,
      });

      success('Payment Verified!', 'Your booking is confirmed and tickets are issued.');
      navigate(`/success/${bookingId}`);
    } catch (err: any) {
      setSubmitting(false);
      const msg = err.response?.data?.detail || 'Signature verification failed. Please retry payment.';
      error('Verification Error', msg);
    }
  };

  const handleSimulatorSuccess = async (paymentId: string, signature: string) => {
    setSimulatorOpen(false);
    if (!currentOrder) return;
    await handlePaymentVerification(
      currentOrder.booking_id,
      currentOrder.razorpay_order_id,
      paymentId,
      signature
    );
  };

  return (
    <div className="py-12 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
      {/* Official UPI QR Payment Modal */}
      {currentOrder && (
        <ManualUpiPaymentModal
          isOpen={upiModalOpen}
          bookingId={currentOrder.booking_id}
          amount={currentOrder.amount}
          upiId={currentOrder.upi_id || config?.upi_id}
          upiQrImageUrl={currentOrder.upi_qr_image_url || config?.upi_qr_image_url || '/api/payments/qr-image'}
          upiInstructions={currentOrder.upi_payment_instructions || config?.upi_payment_instructions}
          customerName={currentOrder.customer_name}
          onSuccess={() => {
            setUpiModalOpen(false);
            navigate(`/success/${currentOrder.booking_id}`);
          }}
          onDismiss={() => {
            setUpiModalOpen(false);
            info('Payment Pending', 'You can submit your payment proof whenever you are ready.');
          }}
        />
      )}

      {/* Razorpay Simulation Modal for test mode */}
      {currentOrder && (
        <RazorpayModalSimulator
          isOpen={simulatorOpen}
          orderId={currentOrder.razorpay_order_id}
          bookingId={currentOrder.booking_id}
          amount={currentOrder.amount}
          customerName={currentOrder.customer_name}
          customerEmail={currentOrder.customer_email}
          customerPhone={currentOrder.customer_phone}
          onSuccess={handleSimulatorSuccess}
          onDismiss={() => {
            setSimulatorOpen(false);
            setSubmitting(false);
            info('Checkout dismissed', 'Payment test simulation cancelled. You can retry whenever ready.');
          }}
        />
      )}

      {/* Header */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#d4af37] px-3.5 py-1 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/25 mb-3">
          <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
          Official E-Ticket Booking Portal
        </div>
        <h1 className="text-3xl sm:text-5xl font-black text-white font-['Outfit']">
          Book Your Entry Passes
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Enter attendee contact details to reserve your cryptographically secured QR entry pass for {config?.event_name || 'GARBA NIGHT 2026'}.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Booking Form (Left) */}
        <div className="lg:col-span-7 glass-panel rounded-3xl p-6 sm:p-8 border border-white/[0.08] shadow-2xl">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Full Name */}
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 font-['Outfit']">
                FULL NAME
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Enter your name"
                  {...register('customer_name')}
                  className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37]/40 transition-all touch-target"
                />
              </div>
              {errors.customer_name && (
                <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {errors.customer_name.message}
                </p>
              )}
            </div>

            {/* Email Address */}
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 font-['Outfit']">
                EMAIL
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  placeholder="Enter your email"
                  {...register('email')}
                  className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37]/40 transition-all touch-target"
                />
              </div>
              {errors.email && (
                <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Phone Number */}
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 font-['Outfit']">
                PHONE
              </label>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="tel"
                  placeholder="Enter phone number"
                  {...register('phone')}
                  className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37]/40 transition-all touch-target"
                />
              </div>
              {errors.phone && (
                <p className="text-xs text-rose-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {errors.phone.message}
                </p>
              )}
            </div>

            {/* Ticket Quantity Stepper */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Number of Passes
                </label>
                <span className="text-xs text-[#d4af37] font-semibold">Max 10 passes per order</span>
              </div>
              <div className={`flex items-center gap-4 p-2 rounded-2xl bg-black/40 border transition-all duration-300 ${
                ticketCount === 10 ? 'border-[#d4af37] shadow-[0_0_20px_rgba(212,175,55,0.25)]' : 'border-white/[0.08]'
              }`}>
                <button
                  type="button"
                  onClick={() => handleStepTickets(-1)}
                  disabled={ticketCount <= 1}
                  className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-white disabled:opacity-30 transition-colors"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <div className="flex-1 text-center">
                  <span className={`text-2xl font-black font-mono transition-colors duration-300 ${
                    ticketCount === 10 ? 'text-[#f3e4b2]' : 'text-white'
                  }`}>{ticketCount}</span>
                  <span className="text-xs text-slate-400 ml-2">Pass{ticketCount > 1 ? 'es' : ''}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleStepTickets(1)}
                  disabled={ticketCount >= 10}
                  className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-white disabled:opacity-30 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>

              {/* Quick Jump to 10 passes group offer if not selected */}
              {ticketCount < 10 && (
                <div className="mt-2.5 flex items-center justify-between px-1">
                  <button
                    type="button"
                    onClick={() => setValue('ticket_count', 10, { shouldValidate: true })}
                    className="text-[11px] font-bold text-[#d4af37] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <Flame className="w-3 h-3 text-amber-400" />
                    <span>Select 10 Passes & Get 1 FREE (Save ₹{ticketPrice})</span>
                  </button>
                </div>
              )}

              {/* Requirement 3 & 4: Dynamic Offer Messages */}
              <div className="mt-3">
                <AnimatePresence mode="wait">
                  {ticketCount === 8 && (
                    <motion.div
                      key="offer-8"
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs font-semibold flex items-center gap-2"
                    >
                      <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
                      <span>You're almost there! Add 2 more tickets to unlock the group offer.</span>
                    </motion.div>
                  )}

                  {ticketCount === 9 && (
                    <motion.div
                      key="offer-9"
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-xs font-bold flex items-center gap-2"
                    >
                      <Gift className="w-4 h-4 text-emerald-400 shrink-0 animate-bounce" />
                      <span>Add 1 more ticket — your 10th ticket is FREE!</span>
                    </motion.div>
                  )}

                  {ticketCount === 10 && (
                    <motion.div
                      key="offer-10"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.3 }}
                      className="p-4 rounded-2xl glass-panel-gold border-2 border-[#d4af37] shadow-[0_0_30px_rgba(212,175,55,0.3)] relative overflow-hidden"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-sm font-black text-white flex items-center gap-1.5 uppercase font-['Outfit']">
                            <span>🎉 GROUP OFFER UNLOCKED</span>
                          </div>
                          <div className="text-xs font-extrabold text-[#d4af37] mt-0.5 uppercase tracking-wider">
                            BUY 10, PAY FOR 9
                          </div>
                        </div>
                        <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 text-xs font-black">
                          SAVE ₹{groupDiscount.toLocaleString('en-IN')}
                        </span>
                      </div>

                      <div className="mt-2.5 flex items-center gap-3 text-xs text-slate-200">
                        <span className="font-semibold text-white">10 Tickets</span>
                        <span>•</span>
                        <span className="text-emerald-300 font-bold">9 Paid + 1 FREE</span>
                      </div>

                      <p className="mt-2 text-[11px] text-slate-300 font-medium">
                        🎉 Group offer unlocked! You get 10 tickets and pay for only 9.
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <button
                type="submit"
                disabled={submitting}
                className="festive-button w-full py-4 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-xl disabled:opacity-50 transition-all cursor-pointer"
              >
                {submitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    <span>{loadingStatusText}</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    <span>PAY NOW • ₹{totalPayable.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Order Summary Card (Right) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-panel-gold rounded-3xl p-6 sm:p-8 border border-[#d4af37]/40 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-black text-white font-['Cinzel'] tracking-wide flex items-center gap-2">
                <Receipt className="w-5 h-5 text-[#d4af37]" />
                <span>YOUR ORDER</span>
              </h3>
              {ticketCount === 10 ? (
                <span className="text-[10px] uppercase font-black tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse">
                  GROUP OFFER APPLIED
                </span>
              ) : (
                <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-[#d4af37]/15 text-[#f3e4b2] border border-[#d4af37]/30">
                  {config?.venue_city || 'Mysuru'}
                </span>
              )}
            </div>

            <div className="text-center pb-4 mb-4 border-b border-white/[0.08]">
              <div className="text-xs font-black text-[#f3e4b2] uppercase tracking-widest font-['Cinzel']">
                {config?.event_name || 'GARBA NIGHT 2026'}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                {config?.event_date || 'October 17, 2026'} • {config?.venue_name || 'Green Acres, Mysuru'}
              </div>
            </div>

            <div className="space-y-3 text-xs text-slate-300 pb-5 border-b border-white/20">
              <div className="flex items-center justify-between">
                <span className="text-slate-300 font-semibold">Early Bird Pass</span>
                <span className="font-mono text-white font-bold">{ticketCount} × ₹{ticketPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400">Ticket Price</span>
                <span className="font-mono text-white font-bold">
                  ₹{ticketSubtotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>

              {ticketCount === 10 && groupDiscount > 0 && (
                <div className="flex items-center justify-between text-emerald-400 font-bold bg-emerald-500/10 px-2 py-1.5 rounded-lg border border-emerald-500/20">
                  <span className="flex items-center gap-1.5">
                    <span>🎉</span>
                    <span>Group Offer (1 Pass Free)</span>
                  </span>
                  <span className="font-mono">
                    -₹{groupDiscount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              )}

              {/* Gateway & Tax Breakdown */}
              <div className="pt-2.5 pb-1 border-t border-white/10 space-y-2">
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>Razorpay Fee (2%)</span>
                  <span className="font-mono text-slate-300">
                    ₹{paymentFee.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>GST on Razorpay Fee (18%)</span>
                  <span className="font-mono text-slate-300">
                    ₹{gstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>

            {/* TOTAL visually prominent */}
            <div className="pt-4 pb-5 flex items-center justify-between">
              <div>
                <div className="text-sm font-black text-white uppercase tracking-wider font-['Outfit']">CUSTOMER PAYS</div>
                <div className="text-[10px] text-[#f3e4b2]/80 font-medium">₹{(totalPayable / ticketCount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / ticket</div>
                {ticketCount === 10 && (
                  <div className="text-[11px] text-emerald-400 font-extrabold mt-0.5">SAVE ₹{groupDiscount.toLocaleString('en-IN')} (1 FREE)</div>
                )}
              </div>
              <div className="text-right">
                <div className="text-3xl sm:text-4xl font-black bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent font-mono">
                  ₹{totalPayable.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {/* CONTINUE TO PAYMENT Button */}
            <button
              type="button"
              onClick={handleSubmit(onSubmit)}
              disabled={submitting}
              className="festive-button w-full py-4 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-2xl shadow-[#d4af37]/30 touch-target cursor-pointer"
            >
              <Lock className="w-4 h-4" />
              <span>CONTINUE TO PAYMENT</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

