import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle,
  XCircle,
  Eye,
  Search,
  RefreshCw,
  AlertTriangle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  FileText,
  X,
  User,
  Phone,
  Mail,
  Ticket,
  Copy,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import {
  fetchPendingPaymentVerifications,
  approvePaymentVerification,
  rejectPaymentVerification,
  fetchAdminPaymentScreenshotBlobUrl
} from '../services/api';
import { PaymentVerificationItem } from '../types';
import { useToast } from '../components/Toast';

export const AdminPaymentVerificationPage: React.FC = () => {
  const { success, error, info } = useToast();
  const [items, setItems] = useState<PaymentVerificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('VERIFICATION_PENDING');
  const [searchTerm, setSearchTerm] = useState('');

  // Action states
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Rejection modal
  const [rejectModalItem, setRejectModalItem] = useState<PaymentVerificationItem | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectSubmitting, setRejectSubmitting] = useState(false);

  // Screenshot viewer modal
  const [screenshotItem, setScreenshotItem] = useState<PaymentVerificationItem | null>(null);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [screenshotLoading, setScreenshotLoading] = useState(false);

  const loadData = (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    fetchPendingPaymentVerifications(filterStatus)
      .then((data) => {
        setItems(data);
        if (showSpinner) setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching verification list:', err);
        if (showSpinner) setLoading(false);
        error('Data Error', 'Failed to load payment verification records.');
      });
  };

  useEffect(() => {
    loadData(true);
  }, [filterStatus]);

  // Handle Approve
  const handleApprove = async (item: PaymentVerificationItem) => {
    if (actionLoadingId) return; // Prevent double clicks
    const confirmed = window.confirm(
      `Approve payment for ${item.customer_name} (${item.booking_id})?\n\nAmount: ₹${item.amount}\nUTR: ${item.utr_number || 'N/A'}\n\nThis will instantly mark the booking as CONFIRMED, generate ${item.ticket_count} tickets with unique QR codes, and send the confirmation email.`
    );
    if (!confirmed) return;

    setActionLoadingId(item.booking_id);
    try {
      const res = await approvePaymentVerification(item.booking_id);
      if (res.success) {
        success('Payment Approved!', `Booking ${item.booking_id} confirmed. Tickets and email generated.`);
        loadData(false);
      } else {
        error('Approval Failed', res.message || 'Could not approve payment.');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Server error during approval.';
      error('Approval Failed', msg);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Open reject modal
  const openRejectModal = (item: PaymentVerificationItem) => {
    setRejectModalItem(item);
    setRejectReason('UTR reference not received in bank account');
  };

  // Submit rejection
  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectModalItem || !rejectReason.trim()) return;

    setRejectSubmitting(true);
    try {
      const res = await rejectPaymentVerification(rejectModalItem.booking_id, rejectReason.trim());
      if (res.success) {
        info('Payment Rejected', `Booking ${rejectModalItem.booking_id} marked as PAYMENT_FAILED.`);
        setRejectModalItem(null);
        setRejectReason('');
        loadData(false);
      } else {
        error('Rejection Failed', res.message || 'Could not reject payment.');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Server error during rejection.';
      error('Rejection Failed', msg);
    } finally {
      setRejectSubmitting(false);
    }
  };

  // View screenshot
  const handleViewScreenshot = async (item: PaymentVerificationItem) => {
    setScreenshotItem(item);
    setScreenshotUrl(null);
    setScreenshotLoading(true);

    try {
      const blobUrl = await fetchAdminPaymentScreenshotBlobUrl(item.booking_id);
      setScreenshotUrl(blobUrl);
    } catch (err) {
      error('Screenshot Error', 'Failed to retrieve protected payment screenshot.');
    } finally {
      setScreenshotLoading(false);
    }
  };

  const closeScreenshotModal = () => {
    if (screenshotUrl) {
      URL.revokeObjectURL(screenshotUrl);
    }
    setScreenshotItem(null);
    setScreenshotUrl(null);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    info('Copied!', `${label} copied to clipboard.`);
  };

  // Filtered list
  const filteredItems = items.filter((item) => {
    if (!searchTerm.trim()) return true;
    const q = searchTerm.toLowerCase();
    return (
      item.booking_id.toLowerCase().includes(q) ||
      item.customer_name.toLowerCase().includes(q) ||
      item.phone.toLowerCase().includes(q) ||
      item.email.toLowerCase().includes(q) ||
      (item.utr_number && item.utr_number.toLowerCase().includes(q))
    );
  });

  const pendingCount = items.filter((i) => i.payment_status === 'VERIFICATION_PENDING').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-wide font-['Outfit'] flex items-center gap-3">
            <span className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <ShieldCheck className="w-6 h-6" />
            </span>
            <span>Manual UPI Payment Verification</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review customer-submitted UTR transaction numbers and payment screenshots before approving tickets.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold flex items-center gap-2 border border-white/10 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Security Warning Notice */}
      <div className="p-4 rounded-2xl bg-amber-500/[0.06] border border-amber-500/20 text-xs text-slate-300 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-bold text-amber-300 uppercase tracking-wide text-[11px]">
            Security Protocol &amp; Verification Rule
          </span>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            The UTR number and screenshot submitted by the customer are declarations, not bank confirmations. Always cross-reference the <strong>UTR / Reference ID</strong> against your official UPI / Bank app account before clicking <strong>APPROVE PAYMENT</strong>.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-4 rounded-2xl glass-panel border border-white/10">
        {/* Status Tabs */}
        <div className="flex p-1 rounded-xl bg-white/[0.04] border border-white/5 overflow-x-auto gap-1">
          <button
            onClick={() => setFilterStatus('VERIFICATION_PENDING')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap flex items-center gap-2 ${
              filterStatus === 'VERIFICATION_PENDING'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Pending Review</span>
            {pendingCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-950/30 font-mono">
                {pendingCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setFilterStatus('PAID')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
              filterStatus === 'PAID'
                ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Approved
          </button>
          <button
            onClick={() => setFilterStatus('REJECTED')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
              filterStatus === 'REJECTED'
                ? 'bg-rose-500 text-white shadow-md shadow-rose-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Rejected
          </button>
          <button
            onClick={() => setFilterStatus('ALL')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
              filterStatus === 'ALL'
                ? 'bg-white/20 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All Submissions
          </button>
        </div>

        {/* Search */}
        <div className="relative flex-1 md:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search Booking, Name, UTR..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-black/40 border border-white/10 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-amber-400 font-mono"
          />
        </div>
      </div>

      {/* Main Table / Cards List */}
      {loading ? (
        <div className="py-24 text-center">
          <div className="w-10 h-10 border-3 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-xs text-slate-400">Loading payment submissions...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="py-20 text-center glass-panel rounded-3xl border border-white/10">
          <CheckCircle2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No Submissions Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {filterStatus === 'VERIFICATION_PENDING'
              ? 'All customer manual payments have been verified! No pending requests.'
              : 'No verification records match your current filter.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item) => {
            const isPending = item.payment_status === 'VERIFICATION_PENDING';
            const isApproved = item.payment_status === 'PAID';
            const isRejected = item.payment_status === 'REJECTED';
            const isWorking = actionLoadingId === item.booking_id;

            return (
              <div
                key={item.booking_id}
                className="p-5 sm:p-6 rounded-3xl glass-panel border border-white/10 hover:border-white/20 transition-all bg-gradient-to-r from-white/[0.02] to-transparent relative overflow-hidden"
              >
                {/* Status Indicator Bar */}
                <div
                  className={`absolute top-0 left-0 right-0 h-1 ${
                    isApproved
                      ? 'bg-emerald-500'
                      : isRejected
                      ? 'bg-rose-500'
                      : 'bg-amber-500'
                  }`}
                />

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-center">
                  {/* Col 1: Booking ID & Timestamp (3 cols) */}
                  <div className="lg:col-span-3 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-base text-amber-400">
                        {item.booking_id}
                      </span>
                      <button
                        onClick={() => copyToClipboard(item.booking_id, 'Booking ID')}
                        className="text-slate-500 hover:text-slate-300 p-1"
                        title="Copy Booking ID"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>

                    <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>{new Date(item.created_at).toLocaleString('en-IN')}</span>
                    </div>

                    <div className="pt-1">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                          isApproved
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                            : isRejected
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/20'
                            : 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                        }`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                        {item.payment_status}
                      </span>
                    </div>
                  </div>

                  {/* Col 2: Customer Details (3 cols) */}
                  <div className="lg:col-span-3 space-y-1 text-xs">
                    <div className="font-bold text-white flex items-center gap-1.5 text-sm">
                      <User className="w-3.5 h-3.5 text-amber-400/80" />
                      <span>{item.customer_name}</span>
                    </div>
                    <div className="text-slate-400 flex items-center gap-1.5 font-mono text-[11px]">
                      <Phone className="w-3 h-3 text-slate-500" />
                      <span>{item.phone}</span>
                    </div>
                    <div className="text-slate-400 flex items-center gap-1.5 text-[11px] truncate">
                      <Mail className="w-3 h-3 text-slate-500" />
                      <span className="truncate">{item.email}</span>
                    </div>
                  </div>

                  {/* Col 3: Passes & Amount (2 cols) */}
                  <div className="lg:col-span-2 space-y-1">
                    <div className="text-xs text-slate-400 flex items-center gap-1.5">
                      <Ticket className="w-3.5 h-3.5 text-amber-400" />
                      <span className="font-bold text-white">{item.ticket_count} Tickets</span>
                    </div>
                    <div className="text-lg font-black text-emerald-400 font-mono">
                      ₹{item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                    <div className="text-[10px] text-slate-500 uppercase font-mono">
                      {item.payment_method}
                    </div>
                  </div>

                  {/* Col 4: UTR & Proof (2 cols) */}
                  <div className="lg:col-span-2 space-y-2">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono tracking-wider">
                        UTR / Transaction ID
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="font-mono text-xs font-bold text-white bg-black/40 px-2 py-0.5 rounded border border-white/10 break-all select-all">
                          {item.utr_number || 'NOT PROVIDED'}
                        </span>
                        {item.utr_number && (
                          <button
                            onClick={() => copyToClipboard(item.utr_number!, 'UTR')}
                            className="text-slate-400 hover:text-white p-1"
                            title="Copy UTR"
                          >
                            <Copy className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div>
                      {Boolean(item.has_screenshot || item.payment_screenshot) ? (
                        <button
                          onClick={() => handleViewScreenshot(item)}
                          className="px-2.5 py-1 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[11px] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Screenshot</span>
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">No screenshot uploaded</span>
                      )}
                    </div>
                  </div>

                  {/* Col 5: Actions (2 cols) */}
                  <div className="lg:col-span-2 flex flex-col sm:flex-row lg:flex-col gap-2 justify-end">
                    {isPending ? (
                      <>
                        <button
                          onClick={() => handleApprove(item)}
                          disabled={isWorking}
                          className="px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 shadow-md shadow-emerald-500/20 transition-all disabled:opacity-50 cursor-pointer"
                        >
                          {isWorking ? (
                            <div className="w-3.5 h-3.5 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                          ) : (
                            <CheckCircle className="w-3.5 h-3.5" />
                          )}
                          <span>APPROVE PAYMENT</span>
                        </button>

                        <button
                          onClick={() => openRejectModal(item)}
                          disabled={isWorking}
                          className="px-3 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold text-xs flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>REJECT PAYMENT</span>
                        </button>
                      </>
                    ) : (
                      <div className="space-y-1 text-right">
                        <Link
                          to={`/admin/bookings/${item.booking_id}`}
                          className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center justify-end gap-1"
                        >
                          <span>Booking Details</span>
                          <ChevronRight className="w-3 h-3" />
                        </Link>
                        {item.verified_by && (
                          <div className="text-[10px] text-slate-500">
                            Verified by: <span className="text-slate-400 font-mono">{item.verified_by}</span>
                          </div>
                        )}
                        {item.rejection_reason && (
                          <div className="text-[10px] text-rose-400/90 bg-rose-500/10 p-1.5 rounded border border-rose-500/20 text-left">
                            <strong>Reason:</strong> {item.rejection_reason}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Screenshot Viewer Modal */}
      {screenshotItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-2xl bg-[#0f0c1b] border border-white/20 rounded-3xl p-6 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  <span>Payment Screenshot Proof</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Booking <span className="font-mono text-amber-400">{screenshotItem.booking_id}</span> ({screenshotItem.customer_name})
                </p>
              </div>

              <button
                onClick={closeScreenshotModal}
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-auto flex items-center justify-center bg-black/60 rounded-2xl border border-white/10 p-4 min-h-[300px]">
              {screenshotLoading ? (
                <div className="text-center">
                  <div className="w-8 h-8 border-3 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Loading secure image...</p>
                </div>
              ) : screenshotUrl ? (
                <img
                  src={screenshotUrl}
                  alt="Customer Payment Screenshot"
                  className="max-h-[65vh] w-auto object-contain rounded-lg shadow-lg"
                />
              ) : (
                <div className="text-xs text-rose-400">Unable to load screenshot.</div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
              <div>
                UTR: <span className="font-mono text-white font-bold">{screenshotItem.utr_number || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2">
                {screenshotUrl && (
                  <a
                    href={screenshotUrl}
                    download={`payment_${screenshotItem.booking_id}.jpg`}
                    className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold"
                  >
                    Download Image
                  </a>
                )}
                <button
                  onClick={closeScreenshotModal}
                  className="px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reject Reason Modal */}
      {rejectModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[#0f0c1b] border border-white/20 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <XCircle className="w-5 h-5 text-rose-400" />
                <span>Reject Payment Submission</span>
              </h3>
              <button
                onClick={() => setRejectModalItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRejectSubmit} className="space-y-4">
              <div className="text-xs text-slate-300">
                You are rejecting payment for{' '}
                <strong className="text-white">{rejectModalItem.customer_name}</strong> (
                <span className="font-mono text-amber-400">{rejectModalItem.booking_id}</span>).
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Select or Enter Reason for Rejection
                </label>
                <div className="space-y-1.5 mb-3">
                  {[
                    'UTR reference not received in bank account',
                    'Payment amount does not match ticket total',
                    'Screenshot is blurry / unreadable / invalid',
                    'Duplicate transaction reference'
                  ].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setRejectReason(preset)}
                      className={`w-full text-left text-xs p-2 rounded-lg border transition-colors ${
                        rejectReason === preset
                          ? 'bg-rose-500/20 border-rose-500/40 text-white font-semibold'
                          : 'bg-white/[0.02] border-white/5 text-slate-400 hover:text-white hover:bg-white/[0.05]'
                      }`}
                    >
                      {preset}
                    </button>
                  ))}
                </div>

                <textarea
                  required
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Enter rejection reason visible to customer..."
                  className="w-full p-3 rounded-xl bg-black/40 border border-white/10 text-white text-xs focus:outline-none focus:border-rose-400 font-sans"
                />
              </div>

              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300">
                The booking will be marked as <strong>PAYMENT_FAILED</strong>. No tickets or emails will be issued. The customer will be able to retry payment submission.
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setRejectModalItem(null)}
                  disabled={rejectSubmitting}
                  className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={rejectSubmitting || !rejectReason.trim()}
                  className="px-5 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-md shadow-rose-500/20"
                >
                  {rejectSubmitting ? (
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5" />
                  )}
                  <span>Confirm Rejection</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
