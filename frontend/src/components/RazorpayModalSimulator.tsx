import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, CreditCard, Smartphone, Building2, CheckCircle2, XCircle, X } from 'lucide-react';

interface RazorpayModalSimulatorProps {
  isOpen: boolean;
  orderId: string;
  bookingId: string;
  amount: number;
  customerName: string;
  customerEmail: string;
  customerPhone: string;
  onSuccess: (paymentId: string, signature: string) => void;
  onDismiss: () => void;
}

export const RazorpayModalSimulator: React.FC<RazorpayModalSimulatorProps> = ({
  isOpen,
  orderId,
  bookingId,
  amount,
  customerName,
  customerEmail,
  customerPhone,
  onSuccess,
  onDismiss,
}) => {
  const [selectedMethod, setSelectedMethod] = useState<'upi' | 'card' | 'netbanking'>('upi');
  const [processing, setProcessing] = useState(false);

  if (!isOpen) return null;

  const handleSimulateSuccess = () => {
    setProcessing(true);
    setTimeout(() => {
      const mockPayId = `pay_sim_${Math.random().toString(36).substring(2, 10)}`;
      const mockSig = `sim_sig_${Math.random().toString(36).substring(2, 12)}`;
      setProcessing(false);
      onSuccess(mockPayId, mockSig);
    }, 1200);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-[#121624] border border-blue-500/30 rounded-2xl max-w-md w-full shadow-2xl overflow-hidden text-slate-100"
        >
          {/* Header */}
          <div className="bg-[#1a2138] p-5 border-b border-white/10 flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xl shadow-md">
                R
              </div>
              <div>
                <div className="font-bold text-base flex items-center gap-1.5 text-white">
                  Razorpay Checkout
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    Test Mode
                  </span>
                </div>
                <div className="text-xs text-slate-400">Garba Night 2026 Ticketing</div>
              </div>
            </div>
            <button onClick={onDismiss} className="text-slate-400 hover:text-white p-1">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Amount Badge */}
          <div className="p-5 bg-gradient-to-r from-blue-950/40 via-[#161d31] to-blue-950/40 border-b border-white/5 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Total Payable Amount</div>
              <div className="text-2xl font-black text-white font-mono">₹{amount.toLocaleString('en-IN')}</div>
            </div>
            <div className="text-right text-xs text-slate-400">
              <div>Booking: <span className="font-mono text-amber-400">{bookingId}</span></div>
              <div>{customerName}</div>
            </div>
          </div>

          {/* Payment Method Selector */}
          <div className="p-5 space-y-4">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Select Payment Option
            </div>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSelectedMethod('upi')}
                className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 ${
                  selectedMethod === 'upi'
                    ? 'border-blue-500 bg-blue-500/15 text-white shadow-md shadow-blue-500/20'
                    : 'border-white/10 bg-white/5 text-slate-400 hover:bg-white/10'
                }`}
              >
                <Smartphone className="w-5 h-5 text-emerald-400" />
                <span className="text-xs font-bold">UPI / QR</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedMethod('card')}
                className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 ${
                  selectedMethod === 'card'
                    ? 'border-blue-500 bg-blue-500/15 text-white shadow-md shadow-blue-500/20'
                    : 'border-white/10 bg-white/5 text-slate-400 hover:bg-white/10'
                }`}
              >
                <CreditCard className="w-5 h-5 text-amber-400" />
                <span className="text-xs font-bold">Cards</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedMethod('netbanking')}
                className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 ${
                  selectedMethod === 'netbanking'
                    ? 'border-blue-500 bg-blue-500/15 text-white shadow-md shadow-blue-500/20'
                    : 'border-white/10 bg-white/5 text-slate-400 hover:bg-white/10'
                }`}
              >
                <Building2 className="w-5 h-5 text-purple-400" />
                <span className="text-xs font-bold">Netbanking</span>
              </button>
            </div>

            {selectedMethod === 'upi' && (
              <div className="p-3.5 rounded-xl bg-black/30 border border-white/5 text-xs text-slate-300 space-y-1.5">
                <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                  <Smartphone className="w-4 h-4" /> Instant UPI Autopay / QR
                </div>
                <div className="text-[11px] text-slate-400">
                  Simulating payment via Google Pay, PhonePe, or Paytm UPI for phone: {customerPhone}
                </div>
              </div>
            )}

            {selectedMethod === 'card' && (
              <div className="p-3.5 rounded-xl bg-black/30 border border-white/5 text-xs text-slate-300 space-y-1.5">
                <div className="font-semibold text-amber-400 flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4" /> Visa / Mastercard / RuPay
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  Card: •••• •••• •••• 4242 (Simulated 3D Secure Verification)
                </div>
              </div>
            )}

            {selectedMethod === 'netbanking' && (
              <div className="p-3.5 rounded-xl bg-black/30 border border-white/5 text-xs text-slate-300 space-y-1.5">
                <div className="font-semibold text-purple-400 flex items-center gap-1.5">
                  <Building2 className="w-4 h-4" /> All Major Indian Banks
                </div>
                <div className="text-[11px] text-slate-400">
                  HDFC, ICICI, SBI, Axis, Kotak Bank simulated portal
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="pt-2 space-y-2">
              <button
                type="button"
                disabled={processing}
                onClick={handleSimulateSuccess}
                className="w-full py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 font-bold text-white shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {processing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Verifying Payment with Bank...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                    Pay ₹{amount.toLocaleString('en-IN')} (Success Test)
                  </>
                )}
              </button>

              <button
                type="button"
                disabled={processing}
                onClick={onDismiss}
                className="w-full py-2.5 rounded-xl bg-white/5 hover:bg-white/10 font-semibold text-slate-400 hover:text-white transition-all text-xs flex items-center justify-center gap-1.5"
              >
                <XCircle className="w-3.5 h-3.5 text-rose-400" />
                Cancel / Simulate Payment Failure
              </button>
            </div>
          </div>

          {/* Footer security badge */}
          <div className="p-3 bg-black/40 border-t border-white/5 text-center text-[10px] text-slate-500 flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>256-Bit SSL Encrypted Razorpay Sandbox Gateway</span>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
