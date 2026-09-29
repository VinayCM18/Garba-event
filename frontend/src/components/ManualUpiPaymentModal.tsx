import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Copy,
  Check,
  CheckCircle2,
  Upload,
  AlertCircle,
  ShieldCheck,
  Clock,
  Sparkles,
  Smartphone,
  Info,
  FileImage,
  Trash2
} from 'lucide-react';
import { submitManualPaymentProof } from '../services/api';
import { useToast } from './Toast';

interface ManualUpiPaymentModalProps {
  isOpen: boolean;
  bookingId: string;
  amount: number;
  upiId?: string;
  upiQrImageUrl?: string;
  upiInstructions?: string;
  customerName: string;
  onSuccess: () => void;
  onDismiss: () => void;
}

export const ManualUpiPaymentModal: React.FC<ManualUpiPaymentModalProps> = ({
  isOpen,
  bookingId,
  amount,
  upiId = '',
  upiQrImageUrl = '/api/payments/qr-image',
  upiInstructions,
  customerName,
  onSuccess,
  onDismiss,
}) => {
  const { error, success } = useToast();
  const [utrNumber, setUtrNumber] = useState('');
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [screenshotPreview, setScreenshotPreview] = useState<string | null>(null);
  const [copiedUpi, setCopiedUpi] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleCopyUpi = () => {
    navigator.clipboard.writeText(upiId);
    setCopiedUpi(true);
    setTimeout(() => setCopiedUpi(false), 2500);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      error('File Too Large', 'Please select an image smaller than 5MB.');
      return;
    }

    // Validate format
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      error('Invalid Format', 'Please upload a JPEG, PNG, or WebP image.');
      return;
    }

    setScreenshotFile(file);
    const reader = new FileReader();
    reader.onload = () => {
      setScreenshotPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveScreenshot = () => {
    setScreenshotFile(null);
    setScreenshotPreview(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUtr = utrNumber.trim();

    if (!cleanUtr) {
      error('UTR Required', 'Please enter your bank UTR / UPI Transaction Reference ID.');
      return;
    }

    if (cleanUtr.length < 6) {
      error('Invalid UTR', 'UTR / Transaction Reference must be at least 6 characters.');
      return;
    }

    try {
      setSubmitting(true);

      const formData = new FormData();
      formData.append('booking_id', bookingId);
      formData.append('utr_number', cleanUtr);
      if (screenshotFile) {
        formData.append('screenshot', screenshotFile);
      }

      await submitManualPaymentProof(formData);

      success(
        'Payment Details Received!',
        'Your transaction reference has been submitted. Your booking will be confirmed upon verification.'
      );
      onSuccess();
    } catch (err: any) {
      setSubmitting(false);
      const detail = err.response?.data?.detail || 'Failed to submit payment proof. Please try again.';
      error('Submission Error', detail);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/85 backdrop-blur-md overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94 }}
          className="bg-[#0f0c1b] border-2 border-[#d4af37]/40 rounded-3xl max-w-lg w-full shadow-[0_0_50px_rgba(212,175,55,0.25)] overflow-hidden text-slate-100 my-auto"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-[#181329] via-[#211a38] to-[#181329] p-5 sm:p-6 border-b border-[#d4af37]/25 flex items-start justify-between relative">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[#f3e4b2] via-[#d4af37] to-[#aa8024] flex items-center justify-center text-[#090710] font-black shadow-lg shadow-[#d4af37]/30">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xl sm:text-2xl font-black text-white font-['Cinzel'] tracking-wide">
                  PAYMENT
                </h3>
                <div className="text-xs text-[#f3e4b2] font-semibold flex items-center gap-1.5 mt-0.5">
                  <span>NAVRANG 2026 • Mysuru</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#d4af37]/20 border border-[#d4af37]/40 font-mono">
                    #{bookingId}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={onDismiss}
              disabled={submitting}
              className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-white/10 transition-colors touch-target"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-5 sm:p-6 max-h-[78vh] overflow-y-auto space-y-6">
            {/* Amount to Pay Section (Section 14 Requirement) */}
            <div className="text-center p-5 rounded-2xl bg-gradient-to-b from-[#1c1630] to-[#120d20] border border-[#d4af37]/40 shadow-inner">
              <div className="text-xs font-bold uppercase tracking-widest text-[#f3e4b2] font-['Cinzel']">
                Amount to Pay
              </div>
              <div className="text-3xl sm:text-5xl font-black text-white font-mono mt-1 drop-shadow-md">
                ₹{amount.toLocaleString('en-IN')}
              </div>
              <div className="mt-3 flex items-center justify-center gap-2">
                <span className="text-xs font-mono text-slate-300 bg-black/40 px-3 py-1.5 rounded-xl border border-white/10">
                  {upiId}
                </span>
                <button
                  type="button"
                  onClick={handleCopyUpi}
                  className="px-3 py-1.5 rounded-xl bg-[#d4af37]/20 hover:bg-[#d4af37]/30 text-[#f3e4b2] text-xs font-bold flex items-center gap-1.5 transition-all border border-[#d4af37]/40"
                >
                  {copiedUpi ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>COPIED</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>COPY UPI ID</span>
                    </>
                  )}
                </button>
              </div>
            </div>

          {/* Payment Instructions (Section 14: 1 to 5 numbered list) */}
          <div className="p-4 rounded-2xl bg-[#130f22] border border-white/[0.08] text-xs space-y-2">
            <div className="text-[11px] font-black uppercase tracking-wider text-[#d4af37] font-['Cinzel'] flex items-center justify-between">
              <span>Payment Instructions</span>
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-bold bg-emerald-500/15 px-2 py-0.5 rounded-full border border-emerald-500/30">
                <ShieldCheck className="w-3 h-3" />
                Secure Payment
              </span>
            </div>
            <ol className="space-y-1.5 text-slate-300 pl-1">
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-[#d4af37]/20 text-[#f3e4b2] font-black text-[10px] flex items-center justify-center shrink-0">1</span>
                <span>Open your UPI app</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-[#d4af37]/20 text-[#f3e4b2] font-black text-[10px] flex items-center justify-center shrink-0">2</span>
                <span>Scan the QR</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-[#d4af37]/20 text-[#f3e4b2] font-black text-[10px] flex items-center justify-center shrink-0">3</span>
                <span>Complete payment</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-[#d4af37]/20 text-[#f3e4b2] font-black text-[10px] flex items-center justify-center shrink-0">4</span>
                <span>Enter UTR</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-[#d4af37]/20 text-[#f3e4b2] font-black text-[10px] flex items-center justify-center shrink-0">5</span>
                <span>Upload screenshot</span>
              </li>
            </ol>
          </div>

          {/* Verification Form */}
          <form onSubmit={handleSubmit} className="space-y-4 pt-2 border-t border-white/10">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-[#d4af37]" />
              After Completing Payment:
            </div>

            {/* UTR Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Enter your UTR / Transaction ID <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                value={utrNumber}
                onChange={(e) => setUtrNumber(e.target.value)}
                placeholder="e.g. 123456789012"
                required
                className="w-full px-4 py-3 rounded-xl bg-white/[0.04] border border-white/15 focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37] text-white text-sm font-mono placeholder:text-slate-500 transition-colors"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Found in your payment app (Google Pay, PhonePe, Paytm) transaction details.
              </p>
            </div>

            {/* Screenshot Upload */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Upload payment screenshot <span className="text-slate-400 font-normal">(Optional / Recommended)</span>
              </label>

              {!screenshotPreview ? (
                <label className="border-2 border-dashed border-white/20 hover:border-[#d4af37]/50 rounded-2xl p-4 flex flex-col items-center justify-center cursor-pointer transition-colors bg-white/[0.02] hover:bg-white/[0.04]">
                  <Upload className="w-6 h-6 text-[#d4af37] mb-1.5" />
                  <span className="text-xs font-bold text-slate-200">Click to upload screenshot</span>
                  <span className="text-[10px] text-slate-400 mt-0.5">JPEG, PNG, or WebP (Max 5MB)</span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              ) : (
                <div className="p-3 rounded-2xl bg-black/50 border border-white/10 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 truncate">
                    <img
                      src={screenshotPreview}
                      alt="Screenshot Preview"
                      className="w-12 h-12 object-cover rounded-lg border border-white/15 shrink-0"
                    />
                    <div className="truncate">
                      <div className="text-xs font-bold text-white truncate">
                        {screenshotFile?.name}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {screenshotFile && (screenshotFile.size / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveScreenshot}
                    className="p-2 rounded-xl text-rose-400 hover:bg-rose-500/15 transition-colors"
                    title="Remove image"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Security Banner */}
            <div className="p-3.5 rounded-xl bg-[#d4af37]/10 border border-[#d4af37]/25 flex items-start gap-2.5 text-xs text-[#f3e4b2]">
              <ShieldCheck className="w-4 h-4 shrink-0 text-[#d4af37] mt-0.5" />
              <div className="leading-relaxed">
                <strong>Important:</strong> Your booking will be confirmed after payment verification.
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full festive-button py-3.5 px-6 rounded-2xl text-xs sm:text-sm font-black uppercase tracking-wider shadow-lg shadow-[#d4af37]/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#090710] border-t-transparent rounded-full animate-spin" />
                  <span>Submitting Payment Details...</span>
                </>
              ) : (
                <span>SUBMIT PAYMENT</span>
              )}
            </button>
          </form>
      </div>
    </motion.div>
      </div >
    </AnimatePresence >
  );
};
