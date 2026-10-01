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
  Receipt,
  Flame,
  CheckCircle2,
  Users,
  Heart,
  Baby,
  Check,
  ChevronLeft,
  ShieldCheck,
  Info
} from 'lucide-react';
import {
  fetchPublicConfig,
  createPaymentOrder,
  verifyPaymentSignature,
  failPaymentOrder,
  calculatePaymentFee,
  FeeCalculation
} from '../services/api';
import { EventConfig, TicketOffer } from '../types';
import { useToast } from '../components/Toast';
import { RazorpayModalSimulator } from '../components/RazorpayModalSimulator';
import { ManualUpiPaymentModal } from '../components/ManualUpiPaymentModal';

// Authoritative Offer metadata & fallback definition
interface OfferItem {
  id: string;
  phase_code: string;
  phase_name: string;
  phase_status: 'ACTIVE' | 'LOCKED' | 'COMING_SOON';
  type: 'STAG' | 'GROUP' | 'COUPLE' | 'KIDS';
  title: string;
  price: number;
  per_unit_passes: number;
  description: string;
  badge: string;
  is_purchasable: boolean;
  requires_id_proof?: boolean;
}

const DEFAULT_OFFERS: OfferItem[] = [
  // Early Bird
  {
    id: 'EARLY_BIRD_STAG',
    phase_code: 'EARLY_BIRD',
    phase_name: 'EARLY BIRD',
    phase_status: 'ACTIVE',
    type: 'STAG',
    title: 'Early Bird — Stag Entry',
    price: 599,
    per_unit_passes: 1,
    description: 'Single person entry.',
    badge: 'EARLY BIRD',
    is_purchasable: true
  },
  {
    id: 'EARLY_BIRD_GROUP_10',
    phase_code: 'EARLY_BIRD',
    phase_name: 'EARLY BIRD',
    phase_status: 'ACTIVE',
    type: 'GROUP',
    title: 'Early Bird — Group of 10',
    price: 4999,
    per_unit_passes: 10,
    description: 'Entry for 10 people.',
    badge: 'BEST VALUE • SAVE ₹991',
    is_purchasable: true
  },
  {
    id: 'EARLY_BIRD_COUPLE',
    phase_code: 'EARLY_BIRD',
    phase_name: 'EARLY BIRD',
    phase_status: 'ACTIVE',
    type: 'COUPLE',
    title: 'Early Bird — Couple Entry',
    price: 999,
    per_unit_passes: 2,
    description: 'Entry for 2 people.',
    badge: 'POPULAR CHOICE',
    is_purchasable: true
  },
  // Phase 1 (Coming Soon)
  {
    id: 'PHASE_1_STAG',
    phase_code: 'PHASE_1',
    phase_name: 'PHASE 1',
    phase_status: 'COMING_SOON',
    type: 'STAG',
    title: 'Phase 1 — Stag Entry',
    price: 799,
    per_unit_passes: 1,
    description: 'Single person entry.',
    badge: 'COMING SOON',
    is_purchasable: false
  },
  {
    id: 'PHASE_1_GROUP_10',
    phase_code: 'PHASE_1',
    phase_name: 'PHASE 1',
    phase_status: 'COMING_SOON',
    type: 'GROUP',
    title: 'Phase 1 — Group of 10',
    price: 6799,
    per_unit_passes: 10,
    description: 'Entry for 10 people.',
    badge: 'COMING SOON',
    is_purchasable: false
  },
  {
    id: 'PHASE_1_COUPLE',
    phase_code: 'PHASE_1',
    phase_name: 'PHASE 1',
    phase_status: 'COMING_SOON',
    type: 'COUPLE',
    title: 'Phase 1 — Couple Entry',
    price: 1399,
    per_unit_passes: 2,
    description: 'Entry for 2 people.',
    badge: 'COMING SOON',
    is_purchasable: false
  },
  // Kids
  {
    id: 'KIDS_5_12',
    phase_code: 'ALL',
    phase_name: 'KIDS (5–12)',
    phase_status: 'ACTIVE',
    type: 'KIDS',
    title: 'Kids (5–12 years)',
    price: 300,
    per_unit_passes: 1,
    description: 'Entry for 1 child aged 5–12 years.',
    badge: 'ID PROOF REQUIRED',
    is_purchasable: true,
    requires_id_proof: true
  }
];

const bookingSchema = z.object({
  customer_name: z.string().min(2, 'Please enter your full name (minimum 2 characters)'),
  email: z.string().email('Please enter a valid email address'),
  phone: z
    .string()
    .regex(/^(?:\+91|91)?[6-9]\d{9}$/, 'Please enter a valid 10-digit Indian phone number (starting 6-9)'),
  quantity: z.number().min(1, 'Minimum quantity is 1').max(10, 'Maximum quantity is 10'),
  child_name: z.string().optional(),
  child_age: z.string().optional()
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
  const [offersList, setOffersList] = useState<OfferItem[]>(DEFAULT_OFFERS);
  const [selectedOfferId, setSelectedOfferId] = useState<string>('EARLY_BIRD_STAG');
  const [bookingStep, setBookingStep] = useState<'OFFERS' | 'DETAILS'>('OFFERS');

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
    setError,
    formState: { errors }
  } = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
    defaultValues: {
      customer_name: '',
      email: '',
      phone: '',
      quantity: 1,
      child_name: '',
      child_age: ''
    }
  });

  const quantity = watch('quantity') || 1;
  const childNameValue = watch('child_name');
  const childAgeValue = watch('child_age');

  // Load public event config and offer definitions from backend
  useEffect(() => {
    fetchPublicConfig()
      .then((cfg) => {
        setConfig(cfg);
        if (cfg.offers && cfg.offers.length > 0) {
          setOffersList(cfg.offers as OfferItem[]);
        }
      })
      .catch((err) => {
        console.error('Failed to load event config:', err);
      });
  }, []);

  // Handle URL query parameters (e.g. /book?offer=EARLY_BIRD_GROUP_10 or ?count=10)
  useEffect(() => {
    const offerParam = searchParams.get('offer');
    if (offerParam) {
      const match = DEFAULT_OFFERS.find((o) => o.id === offerParam.toUpperCase());
      if (match && match.is_purchasable) {
        setSelectedOfferId(match.id);
        setBookingStep('DETAILS');
      }
    } else {
      const countParam = searchParams.get('count');
      if (countParam === '10') {
        setSelectedOfferId('EARLY_BIRD_GROUP_10');
        setBookingStep('DETAILS');
      }
    }
  }, [searchParams]);

  // Selected Offer reference
  const selectedOffer = offersList.find((o) => o.id === selectedOfferId) || DEFAULT_OFFERS[0];
  const isKidsOffer = selectedOffer.type === 'KIDS';
  const isGroupOffer = selectedOffer.type === 'GROUP';
  const isCoupleOffer = selectedOffer.type === 'COUPLE';

  // Trigger celebratory confetti when group offer is chosen
  const prevOfferRef = useRef(selectedOfferId);
  useEffect(() => {
    if (selectedOfferId === 'EARLY_BIRD_GROUP_10' && prevOfferRef.current !== 'EARLY_BIRD_GROUP_10') {
      try {
        confetti({
          particleCount: 50,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#d4af37', '#f3e4b2', '#10b981', '#ffffff']
        });
      } catch (e) {
        // confetti fallback
      }
    }
    prevOfferRef.current = selectedOfferId;
  }, [selectedOfferId]);

  // Authoritatively recalculate fee whenever offer or quantity changes
  useEffect(() => {
    let isCurrent = true;
    setCalculatingFee(true);
    calculatePaymentFee(
      selectedOffer.per_unit_passes * quantity,
      selectedOffer.phase_code,
      selectedOffer.id,
      quantity
    )
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
  }, [selectedOfferId, quantity, selectedOffer.per_unit_passes, selectedOffer.phase_code, selectedOffer.id]);

  const ticketSubtotal = pricing?.ticket_subtotal ?? selectedOffer.price * quantity;
  const totalPayable = pricing?.total_amount ?? ticketSubtotal;
  const totalPasses = pricing?.passes_count ?? selectedOffer.per_unit_passes * quantity;

  const handleSelectOffer = (offer: OfferItem) => {
    if (!offer.is_purchasable) {
      info('Coming Soon', `${offer.title} is not active yet. Please select an available Early Bird offer.`);
      return;
    }
    setSelectedOfferId(offer.id);
    setValue('quantity', 1);
  };

  const handleProceedToDetails = () => {
    if (!selectedOffer.is_purchasable) {
      error('Offer Locked', 'Please select an available Early Bird offer.');
      return;
    }
    setBookingStep('DETAILS');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleStepQuantity = (delta: number) => {
    const current = quantity || 1;
    const maxQty = isGroupOffer ? 2 : isCoupleOffer ? 3 : 5;
    const next = Math.max(1, Math.min(maxQty, current + delta));
    setValue('quantity', next, { shouldValidate: true });
  };

  const onSubmit = async (data: BookingFormData) => {
    if (!selectedOffer.is_purchasable) {
      error('Offer Inactive', 'The selected ticket phase is currently locked.');
      return;
    }

    // Kids Offer Validation
    if (isKidsOffer) {
      if (!data.child_name || data.child_name.trim().length < 2) {
        setError('child_name', { message: "Please enter the child's full name" });
        return;
      }
      const ageNum = parseInt(data.child_age || '0', 10);
      if (isNaN(ageNum) || ageNum < 5 || ageNum > 12) {
        setError('child_age', { message: 'Child age must be between 5 and 12 years' });
        return;
      }
    }

    try {
      setSubmitting(true);
      setLoadingStatusText('Reserving inventory & generating Razorpay order...');

      const idempotencyKey = `order_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

      const orderPayload: any = {
        customer_name: data.customer_name,
        email: data.email,
        phone: data.phone,
        offer_id: selectedOffer.id,
        quantity: data.quantity,
        ticket_phase: selectedOffer.phase_code,
        idempotency_key: idempotencyKey
      };

      if (isKidsOffer) {
        orderPayload.child_name = data.child_name?.trim();
        orderPayload.child_age = parseInt(data.child_age || '5', 10);
      }

      const orderResponse = await createPaymentOrder(orderPayload);
      setCurrentOrder(orderResponse);
      setSubmitting(false);

      // Real Razorpay Live/Test Checkout Flow
      const launchRazorpay = () => {
        const options = {
          key: orderResponse.key_id,
          amount: Math.round(orderResponse.amount * 100),
          currency: orderResponse.currency || 'INR',
          name: config?.event_name || 'NAVRANG 2026',
          description: `${orderResponse.offer_title || selectedOffer.title} • ${totalPasses} Admission Pass${totalPasses > 1 ? 'es' : ''}`,
          order_id: orderResponse.razorpay_order_id,
          prefill: {
            name: data.customer_name,
            email: data.email,
            contact: data.phone
          },
          notes: {
            booking_id: orderResponse.booking_id,
            offer_id: selectedOffer.id,
            offer_title: selectedOffer.title,
            passes_count: String(totalPasses),
            event: 'NAVRANG 2026 in collaboration with The Happy Circle',
            phase: selectedOffer.phase_code
          },
          theme: {
            color: '#d4af37'
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
            }
          }
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
          error('Payment Failed', reason + ' Your booking has not been confirmed. Please retry.');
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
        razorpay_signature: signature
      });

      success('Payment Verified!', 'Your booking is confirmed and official tickets are issued.');
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

  // Group offers into categories
  const earlyBirdOffers = offersList.filter((o) => o.phase_code === 'EARLY_BIRD');
  const phase1Offers = offersList.filter((o) => o.phase_code === 'PHASE_1');
  const kidsOffers = offersList.filter((o) => o.type === 'KIDS');

  return (
    <div className="py-10 sm:py-16 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
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

      {/* Top Header */}
      <div className="text-center max-w-3xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#d4af37] px-4 py-1.5 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/25 mb-4 shadow-sm backdrop-blur-md">
          <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
          <span>Official E-Ticket Booking Portal</span>
        </div>

        {/* Event Collaboration Crest */}
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-full overflow-hidden border border-[#d4af37]/60 shadow-md bg-black shrink-0">
              <img
                src="/heritage_productions.jpg"
                alt="Heritage Productions"
                className="w-full h-full object-cover"
              />
            </div>
            <span className="text-xs text-[#d4af37] font-bold font-mono">×</span>
            <div className="w-9 h-9 rounded-full overflow-hidden border border-[#d4af37]/60 shadow-md p-0.5 bg-black shrink-0">
              <img
                src="/images/happy-circle-logo.png"
                alt="The Happy Circle Logo"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
          <div className="text-left">
            <div className="text-lg sm:text-xl font-extrabold uppercase font-['Cinzel'] tracking-wider bg-gradient-to-r from-white via-[#f7e8c3] to-[#d4af37] bg-clip-text text-transparent leading-tight">
              NAVRANG 2026
            </div>
            <div className="text-[10px] text-[#e5c97b] font-bold uppercase tracking-[0.14em]">
              in collaboration with The Happy Circle
            </div>
          </div>
        </div>

        <h1 className="text-3xl sm:text-5xl font-black text-white font-['Outfit'] mt-2">
          {bookingStep === 'OFFERS' ? 'Choose Your Offer' : 'Attendee Details & Payment'}
        </h1>
        <p className="mt-2 text-xs sm:text-sm text-slate-400">
          {bookingStep === 'OFFERS'
            ? 'Select your preferred pass package below to continue with encrypted instant QR ticketing.'
            : 'Enter attendee contact information to generate official cryptographic QR admission passes.'}
        </p>

        {/* Breadcrumb Steps */}
        <div className="mt-6 inline-flex items-center gap-3 px-4 py-1.5 rounded-full bg-black/40 border border-white/10 text-xs">
          <button
            type="button"
            onClick={() => setBookingStep('OFFERS')}
            className={`font-bold transition-colors ${
              bookingStep === 'OFFERS' ? 'text-[#d4af37]' : 'text-slate-400 hover:text-white'
            }`}
          >
            1. Select Offer
          </button>
          <span className="text-slate-600">→</span>
          <span className={`font-bold ${bookingStep === 'DETAILS' ? 'text-[#d4af37]' : 'text-slate-500'}`}>
            2. Details & Payment
          </span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* STAGE 1: OFFER SELECTION INTERFACE                                        */}
      {/* ========================================================================= */}
      {bookingStep === 'OFFERS' && (
        <div className="space-y-12">
          {/* SECTION 1: EARLY BIRD (ACTIVE) */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <div className="inline-flex items-center gap-1.5 text-[11px] font-black uppercase tracking-widest text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  AVAILABLE NOW
                </div>
                <h2 className="text-xl sm:text-2xl font-black text-white font-['Cinzel'] tracking-wide mt-0.5">
                  EARLY BIRD OFFERS
                </h2>
              </div>
              <span className="text-xs text-slate-400">Tax-Inclusive Pricing</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {earlyBirdOffers.map((offer) => {
                const isSelected = selectedOfferId === offer.id;
                return (
                  <div
                    key={offer.id}
                    onClick={() => handleSelectOffer(offer)}
                    className={`relative rounded-3xl p-6 transition-all duration-300 cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? 'glass-panel-gold border-2 border-[#d4af37] shadow-[0_0_35px_rgba(212,175,55,0.35)] scale-[1.02]'
                        : 'glass-panel border border-white/[0.08] hover:border-white/20 hover:scale-[1.01]'
                    }`}
                  >
                    {/* Badge */}
                    <div className="flex items-center justify-between mb-4">
                      <span
                        className={`text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full ${
                          isSelected
                            ? 'bg-[#d4af37] text-black shadow-sm'
                            : 'bg-white/10 text-[#f3e4b2] border border-white/10'
                        }`}
                      >
                        {offer.badge}
                      </span>
                      {isSelected ? (
                        <span className="w-6 h-6 rounded-full bg-[#d4af37] text-black flex items-center justify-center shadow-md">
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        </span>
                      ) : (
                        <span className="w-6 h-6 rounded-full border border-white/20" />
                      )}
                    </div>

                    <div>
                      <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                        {offer.type === 'GROUP' ? 'Group Pass' : offer.type === 'COUPLE' ? 'Couple Pass' : 'Single Pass'}
                      </div>
                      <h3 className="text-xl font-black text-white mt-1 font-['Outfit']">{offer.title}</h3>
                      <p className="text-xs text-slate-300 mt-2 leading-relaxed">{offer.description}</p>
                    </div>

                    <div className="mt-6 pt-5 border-t border-white/[0.08]">
                      <div className="flex items-baseline justify-between">
                        <div>
                          <div className="text-3xl font-black text-white font-mono">
                            ₹{offer.price.toLocaleString('en-IN')}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            {offer.per_unit_passes} {offer.per_unit_passes === 1 ? 'person pass' : 'people passes'}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectOffer(offer);
                          }}
                          className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all ${
                            isSelected
                              ? 'bg-[#d4af37] text-black shadow-lg shadow-[#d4af37]/30'
                              : 'bg-white/10 text-white hover:bg-white/20'
                          }`}
                        >
                          {isSelected ? 'SELECTED ✓' : 'SELECT'}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SECTION 2: PHASE 1 (COMING SOON / DISABLED) */}
          <div className="space-y-4 opacity-75">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <div className="inline-flex items-center gap-1.5 text-[11px] font-black uppercase tracking-widest text-amber-400">
                  <Lock className="w-3 h-3 text-amber-400" />
                  COMING SOON
                </div>
                <h2 className="text-xl sm:text-2xl font-black text-slate-300 font-['Cinzel'] tracking-wide mt-0.5">
                  PHASE 1 (NEXT TIER)
                </h2>
              </div>
              <span className="text-xs text-amber-400/80 font-bold px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
                UNLOCKS AFTER EARLY BIRD
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {phase1Offers.map((offer) => (
                <div
                  key={offer.id}
                  className="relative rounded-3xl p-6 bg-[#080a12]/80 border border-white/[0.06] select-none flex flex-col justify-between cursor-not-allowed group"
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
                      COMING SOON
                    </span>
                    <Lock className="w-4 h-4 text-slate-500" />
                  </div>

                  <div>
                    <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">
                      {offer.type === 'GROUP' ? 'Group Pass' : offer.type === 'COUPLE' ? 'Couple Pass' : 'Single Pass'}
                    </div>
                    <h3 className="text-xl font-black text-slate-300 mt-1 font-['Outfit']">{offer.title}</h3>
                    <p className="text-xs text-slate-500 mt-2 leading-relaxed">{offer.description}</p>
                  </div>

                  <div className="mt-6 pt-5 border-t border-white/[0.06]">
                    <div className="flex items-baseline justify-between">
                      <div>
                        <div className="text-2xl font-black text-slate-400 font-mono">
                          ₹{offer.price.toLocaleString('en-IN')}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {offer.per_unit_passes} {offer.per_unit_passes === 1 ? 'person pass' : 'people passes'}
                        </div>
                      </div>
                      <span className="px-3.5 py-1.5 rounded-xl text-[11px] font-bold uppercase tracking-wider bg-white/5 text-slate-500 border border-white/5">
                        LOCKED
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SECTION 3: KIDS (5–12 YEARS) */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div>
                <div className="inline-flex items-center gap-1.5 text-[11px] font-black uppercase tracking-widest text-[#d4af37]">
                  <Baby className="w-3.5 h-3.5 text-[#d4af37]" />
                  CHILD ENTRY PASS
                </div>
                <h2 className="text-xl sm:text-2xl font-black text-white font-['Cinzel'] tracking-wide mt-0.5">
                  KIDS ADMISSION (5–12 YEARS)
                </h2>
              </div>
              <span className="text-xs text-slate-400">Under 5 Years Free</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {kidsOffers.map((offer) => {
                const isSelected = selectedOfferId === offer.id;
                return (
                  <div
                    key={offer.id}
                    onClick={() => handleSelectOffer(offer)}
                    className={`relative rounded-3xl p-6 transition-all duration-300 cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? 'glass-panel-gold border-2 border-[#d4af37] shadow-[0_0_35px_rgba(212,175,55,0.35)] scale-[1.01]'
                        : 'glass-panel border border-white/[0.08] hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <span
                        className={`text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full ${
                          isSelected
                            ? 'bg-[#d4af37] text-black shadow-sm'
                            : 'bg-white/10 text-[#f3e4b2] border border-white/10'
                        }`}
                      >
                        {offer.badge}
                      </span>
                      {isSelected ? (
                        <span className="w-6 h-6 rounded-full bg-[#d4af37] text-black flex items-center justify-center shadow-md">
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        </span>
                      ) : (
                        <span className="w-6 h-6 rounded-full border border-white/20" />
                      )}
                    </div>

                    <div>
                      <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                        Child Pass • Age 5–12
                      </div>
                      <h3 className="text-xl font-black text-white mt-1 font-['Outfit']">
                        Kids (5–12 years) — ₹{offer.price}
                      </h3>
                      <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                        Dedicated admission pass for one child between 5 and 12 years of age.
                      </p>
                      <div className="mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs font-semibold flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                        <span>Aadhaar card / valid ID proof required at entry.</span>
                      </div>
                    </div>

                    <div className="mt-6 pt-5 border-t border-white/[0.08]">
                      <div className="flex items-baseline justify-between">
                        <div>
                          <div className="text-3xl font-black text-white font-mono">
                            ₹{offer.price.toLocaleString('en-IN')}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">Per child pass</div>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectOffer(offer);
                          }}
                          className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all ${
                            isSelected
                              ? 'bg-[#d4af37] text-black shadow-lg shadow-[#d4af37]/30'
                              : 'bg-white/10 text-white hover:bg-white/20'
                          }`}
                        >
                          {isSelected ? 'SELECTED ✓' : 'SELECT'}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Information Card */}
              <div className="rounded-3xl p-6 glass-panel border border-white/[0.08] flex flex-col justify-between">
                <div>
                  <div className="inline-flex items-center gap-2 text-xs font-bold text-[#d4af37] mb-2 uppercase tracking-wider">
                    <Info className="w-4 h-4" />
                    <span>Important Guidelines</span>
                  </div>
                  <h4 className="text-base font-bold text-white mb-2">Child & Family Admission Policy</h4>
                  <ul className="space-y-2 text-xs text-slate-300 leading-relaxed">
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span>Children under 5 years enjoy complimentary entry accompanied by parent/guardian.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span>Aadhaar card or school ID required for verification at turnstiles.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span>Child passes do not mix with adult bundle quantities.</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Sticky/Prominent Bottom Action Bar */}
          <div className="glass-panel-gold rounded-3xl p-6 sm:p-8 border border-[#d4af37]/50 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-[#d4af37]/20 border border-[#d4af37]/40 flex items-center justify-center shrink-0">
                <Ticket className="w-6 h-6 text-[#d4af37]" />
              </div>
              <div>
                <div className="text-xs uppercase font-extrabold text-[#d4af37] tracking-wider">
                  Selected Package
                </div>
                <div className="text-lg sm:text-xl font-black text-white font-['Outfit']">
                  {selectedOffer.title} • ₹{selectedOffer.price.toLocaleString('en-IN')}
                </div>
                <div className="text-xs text-slate-300">
                  {selectedOffer.per_unit_passes} Admission Pass{selectedOffer.per_unit_passes > 1 ? 'es' : ''} • Taxes Included
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleProceedToDetails}
              className="festive-button w-full sm:w-auto px-10 py-4 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-3 shadow-2xl shadow-[#d4af37]/40 hover:scale-105 transition-all cursor-pointer"
            >
              <span>CONTINUE TO BOOK</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STAGE 2: ATTENDEE DETAILS & CHECKOUT FLOW                                 */}
      {/* ========================================================================= */}
      {bookingStep === 'DETAILS' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Booking Form (Left 7 Cols) */}
          <div className="lg:col-span-7 glass-panel rounded-3xl p-6 sm:p-8 border border-white/[0.08] shadow-2xl">
            {/* Offer banner with Change Offer button */}
            <div className="p-4 rounded-2xl bg-black/40 border border-[#d4af37]/30 flex items-center justify-between mb-6">
              <div>
                <div className="text-[10px] uppercase font-bold text-[#d4af37] tracking-wider">
                  SELECTED OFFER
                </div>
                <div className="text-base font-black text-white">{selectedOffer.title}</div>
                <div className="text-xs text-slate-400">
                  {selectedOffer.per_unit_passes} Pass{selectedOffer.per_unit_passes > 1 ? 'es' : ''} per unit • ₹{selectedOffer.price}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setBookingStep('OFFERS')}
                className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-[#d4af37] border border-[#d4af37]/40 hover:bg-[#d4af37]/10 transition-colors flex items-center gap-1 cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Change</span>
              </button>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Full Name */}
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 font-['Outfit']">
                  {isKidsOffer ? 'PARENT / GUARDIAN NAME' : 'PRIMARY ATTENDEE NAME'}
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Enter full name"
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
                  EMAIL ADDRESS (FOR QR TICKETS & PDF)
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    placeholder="Enter email address"
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
                  PHONE NUMBER (10-DIGIT MOBILE)
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="tel"
                    placeholder="Enter 10-digit phone number"
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

              {/* Dedicated Child Details if Kids Offer */}
              {isKidsOffer && (
                <div className="p-4 rounded-2xl bg-[#d4af37]/10 border border-[#d4af37]/30 space-y-4">
                  <div className="flex items-center gap-2 text-xs font-extrabold text-[#f3e4b2] uppercase tracking-wider">
                    <Baby className="w-4 h-4 text-[#d4af37]" />
                    <span>Child Attendee Information</span>
                  </div>
                  <p className="text-xs text-slate-300">
                    Aadhaar card / valid ID proof required at entry for verification.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block text-[11px] font-bold text-slate-300 uppercase mb-1">
                        Child's Full Name
                      </label>
                      <input
                        type="text"
                        placeholder="Child name"
                        {...register('child_name')}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37]"
                      />
                      {errors.child_name && (
                        <p className="text-xs text-rose-400 mt-1">{errors.child_name.message}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-slate-300 uppercase mb-1">
                        Age (5–12)
                      </label>
                      <input
                        type="number"
                        min={5}
                        max={12}
                        placeholder="Age"
                        {...register('child_age')}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37]"
                      />
                      {errors.child_age && (
                        <p className="text-xs text-rose-400 mt-1">{errors.child_age.message}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Quantity Stepper */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    {isGroupOffer ? 'Number of Groups' : isCoupleOffer ? 'Number of Couples' : 'Quantity'}
                  </label>
                  <span className="text-xs text-[#d4af37] font-semibold">
                    {totalPasses} Admission Pass{totalPasses > 1 ? 'es' : ''} total
                  </span>
                </div>
                <div className="flex items-center gap-4 p-2 rounded-2xl bg-black/40 border border-white/[0.08]">
                  <button
                    type="button"
                    onClick={() => handleStepQuantity(-1)}
                    disabled={quantity <= 1}
                    className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-white disabled:opacity-30 transition-colors cursor-pointer"
                  >
                    <Minus className="w-4 h-4" />
                  </button>
                  <div className="flex-1 text-center">
                    <span className="text-2xl font-black font-mono text-white">{quantity}</span>
                    <span className="text-xs text-slate-400 ml-2">
                      {isGroupOffer
                        ? `Group${quantity > 1 ? 's' : ''} (10 passes/group)`
                        : isCoupleOffer
                        ? `Couple${quantity > 1 ? 's' : ''} (2 passes/couple)`
                        : `Pass${quantity > 1 ? 'es' : ''}`}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleStepQuantity(1)}
                    disabled={quantity >= (isGroupOffer ? 2 : isCoupleOffer ? 3 : 5)}
                    className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center text-white disabled:opacity-30 transition-colors cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
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

          {/* Order Summary Card (Right 5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="glass-panel-gold rounded-3xl p-6 sm:p-8 border border-[#d4af37]/40 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-black text-white font-['Cinzel'] tracking-wide flex items-center gap-2">
                  <Receipt className="w-5 h-5 text-[#d4af37]" />
                  <span>YOUR SELECTION</span>
                </h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-[#d4af37]/15 text-[#f3e4b2] border border-[#d4af37]/30">
                  {selectedOffer.phase_name}
                </span>
              </div>

              {/* Event Subheader */}
              <div className="text-center pb-4 mb-4 border-b border-white/[0.08]">
                <div className="text-xs font-black text-[#f3e4b2] uppercase tracking-widest font-['Cinzel']">
                  {config?.event_name || 'NAVRANG 2026'}
                </div>
                <div className="text-[10px] text-[#e5c97b] font-bold uppercase tracking-wider mt-0.5">
                  in collaboration with The Happy Circle
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  {config?.event_date || 'October 17, 2026'} • {config?.venue_name || 'Green Acres, Mysuru'}
                </div>
              </div>

              {/* Selected Offer Info */}
              <div className="p-3.5 rounded-2xl bg-black/40 border border-white/10 mb-4">
                <div className="text-xs text-slate-400 uppercase font-semibold">Package</div>
                <div className="text-base font-black text-white mt-0.5">{selectedOffer.title}</div>
                <div className="text-xs text-[#34d399] font-bold mt-1">
                  {totalPasses} Individual QR Admission Pass{totalPasses > 1 ? 'es' : ''}
                </div>
                {isKidsOffer && (
                  <div className="text-[11px] text-amber-300 font-semibold mt-1">
                    ℹ️ Aadhaar card / valid ID proof required at entry.
                  </div>
                )}
              </div>

              {/* Price Breakdown */}
              <div className="space-y-3 text-xs text-slate-300 pb-5 border-b border-white/20">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-semibold">Offer Price</span>
                  <span className="font-mono text-white font-bold">
                    {quantity} × ₹{selectedOffer.price.toLocaleString('en-IN')}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Taxes</span>
                  <span className="text-emerald-400 font-bold">Included</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Convenience Fee</span>
                  <span className="text-emerald-400 font-bold">₹0.00 (Waived)</span>
                </div>
              </div>

              {/* TOTAL visually prominent */}
              <div className="pt-4 pb-5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-black text-white uppercase tracking-wider font-['Outfit']">
                    TOTAL AMOUNT
                  </div>
                  <div className="text-[11px] text-[#f3e4b2]/80 font-medium">
                    All-Inclusive • Official QR Entry
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl sm:text-4xl font-black bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent font-mono">
                    ₹{totalPayable.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              {/* Security Banner */}
              <div className="p-3 rounded-xl bg-white/[0.04] border border-white/10 mb-5 flex items-center gap-2 text-xs text-slate-300">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Secured via Razorpay 256-bit encryption</span>
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
      )}
    </div>
  );
};
