import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  Mail,
  Ban,
  ShieldCheck,
  CheckCircle2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  QrCode,
  Calendar,
  Clock,
  MapPin,
  ExternalLink,
  Bell,
  Eye,
  Copy,
  X
} from 'lucide-react';
import {
  fetchAdminBookingDetails,
  resendBookingEmail,
  resendOwnerAlert,
  cancelBooking,
  approvePaymentVerification,
  rejectPaymentVerification,
  fetchAdminPaymentScreenshotBlobUrl
} from '../services/api';
import { Booking } from '../types';
import { useToast } from '../components/Toast';

export const AdminBookingDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success, error, info } = useToast();

  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);

  // Manual UPI verification states
  const [approving, setApproving] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('UTR reference not received in bank account');
  const [rejecting, setRejecting] = useState(false);
  const [screenshotModalOpen, setScreenshotModalOpen] = useState(false);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [screenshotLoading, setScreenshotLoading] = useState(false);

  const loadBooking = () => {
    if (!id) return;
    setLoading(true);
    fetchAdminBookingDetails(id)
      .then((data) => {
        setBooking(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching booking details:', err);
        setLoading(false);
        error('Not Found', 'Could not locate booking details.');
      });
  };

  useEffect(() => {
    loadBooking();
  }, [id]);

  const handleApprovePayment = async () => {
    if (!booking || approving) return;
    const ok = window.confirm(
      `Approve payment for booking ${booking.booking_id}?\n\nAmount: ₹${booking.amount}\nUTR: ${booking.utr_number || 'N/A'}\n\nThis will mark the booking as CONFIRMED, generate all tickets with unique QR codes, and send the confirmation email.`
    );
    if (!ok) return;

    setApproving(true);
    try {
      const res = await approvePaymentVerification(booking.booking_id);
      if (res.success) {
        success('Payment Approved', `Booking ${booking.booking_id} is now CONFIRMED. Tickets generated.`);
        loadBooking();
      } else {
        error('Approval Failed', res.message || 'Could not approve payment.');
      }
    } catch (err: any) {
      error('Error', err.response?.data?.detail || err.message || 'Failed to approve payment.');
    } finally {
      setApproving(false);
    }
  };

  const handleRejectPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!booking || !rejectReason.trim() || rejecting) return;

    setRejecting(true);
    try {
      const res = await rejectPaymentVerification(booking.booking_id, rejectReason.trim());
      if (res.success) {
        info('Payment Rejected', `Booking ${booking.booking_id} marked as PAYMENT_FAILED.`);
        setRejectModalOpen(false);
        loadBooking();
      } else {
        error('Rejection Failed', res.message || 'Could not reject payment.');
      }
    } catch (err: any) {
      error('Error', err.response?.data?.detail || err.message || 'Failed to reject payment.');
    } finally {
      setRejecting(false);
    }
  };

  const handleViewScreenshot = async () => {
    if (!booking) return;
    setScreenshotModalOpen(true);
    setScreenshotUrl(null);
    setScreenshotLoading(true);
    try {
      const url = await fetchAdminPaymentScreenshotBlobUrl(booking.booking_id);
      setScreenshotUrl(url);
    } catch (err) {
      error('Screenshot Error', 'Failed to retrieve payment screenshot.');
    } finally {
      setScreenshotLoading(false);
    }
  };

  const handleResend = async () => {
    if (!booking) return;
    try {
      const res = await resendBookingEmail(booking.booking_id);
      if (res.success) {
        success('Email Sent', res.message);
        loadBooking();
      } else {
        error('Failed', res.message);
      }
    } catch (err: any) {
      error('Error', 'Could not resend confirmation email.');
    }
  };

  const handleResendOwner = async () => {
    if (!booking) return;
    try {
      const res = await resendOwnerAlert(booking.booking_id);
      if (res.success) {
        success('Owner Alert Sent', res.message);
        loadBooking();
      } else {
        error('Failed', res.message);
      }
    } catch (err: any) {
      error('Error', 'Could not dispatch owner alert notification.');
    }
  };

  const handleCancel = async () => {
    if (!booking) return;
    if (!window.confirm(`Are you sure you want to cancel booking ${booking.booking_id}? All issued tickets will be invalidated.`)) {
      return;
    }
    try {
      const res = await cancelBooking(booking.booking_id);
      if (res.success) {
        info('Booking Cancelled', res.message);
        loadBooking();
      }
    } catch (err: any) {
      error('Error', 'Could not cancel booking.');
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-10 h-10 border-3 border-amber-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-slate-400">Loading booking records...</p>
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="py-20 text-center">
        <h3 className="text-lg font-bold text-white mb-2">Booking Not Found</h3>
        <Link to="/admin/bookings" className="text-xs font-semibold text-amber-400">
          ← Back to all bookings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top back bar & quick actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <Link
          to="/admin/bookings"
          className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1.5"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Bookings</span>
        </Link>

        <div className="flex items-center gap-2 flex-wrap">
          {(booking.booking_status === 'PAYMENT_VERIFICATION_PENDING' || booking.payment_status === 'VERIFICATION_PENDING') && (
            <>
              <button
                onClick={handleApprovePayment}
                disabled={approving}
                className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md shadow-emerald-500/20 cursor-pointer disabled:opacity-50"
              >
                {approving ? (
                  <div className="w-3.5 h-3.5 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                ) : (
                  <CheckCircle className="w-3.5 h-3.5" />
                )}
                <span>APPROVE PAYMENT</span>
              </button>

              <button
                onClick={() => setRejectModalOpen(true)}
                className="px-3.5 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-bold flex items-center gap-1.5 border border-rose-500/30 cursor-pointer"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>REJECT PAYMENT</span>
              </button>
            </>
          )}

          <a
            href={`/api/bookings/${booking.booking_id}/pdf`}
            download
            className="px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download All Tickets PDF</span>
          </a>

          <button
            onClick={handleResend}
            className="px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-amber-400 hover:text-amber-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Mail className="w-3.5 h-3.5" />
            <span>Resend Customer Email</span>
          </button>

          <button
            onClick={handleResendOwner}
            className="px-3.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-emerald-400 hover:text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Bell className="w-3.5 h-3.5" />
            <span>Resend Owner Alert</span>
          </button>

          {booking.booking_status !== 'CANCELLED' && (
            <button
              onClick={handleCancel}
              className="px-3.5 py-2 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-400 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <Ban className="w-3.5 h-3.5" />
              <span>Cancel Booking</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Details Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Customer Information */}
        <div className="p-6 rounded-3xl glass-panel border border-white/10 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-amber-400 font-['Outfit']">
            Customer Information
          </h3>

          <div className="space-y-3 text-xs">
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Primary Attendee</div>
              <div className="text-sm font-bold text-white mt-0.5">{booking.customer_name}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Email Address</div>
              <div className="font-semibold text-slate-300 mt-0.5">{booking.email}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Mobile Phone</div>
              <div className="font-mono text-slate-300 mt-0.5">{booking.phone}</div>
            </div>
            {booking.child_name && (
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200">
                <div className="text-[10px] uppercase font-bold text-amber-400">Child Attendee</div>
                <div className="font-bold text-white mt-0.5">{booking.child_name} (Age: {booking.child_age || '5–12'})</div>
                <div className="text-[10px] text-slate-400 mt-0.5">Aadhaar card / valid ID required at gate.</div>
              </div>
            )}
          </div>
        </div>

        {/* Booking Meta */}
        <div className="p-6 rounded-3xl glass-panel border border-white/10 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-amber-400 font-['Outfit']">
            Booking Particulars
          </h3>

          <div className="space-y-3 text-xs">
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Booking Reference</div>
              <div className="text-base font-black text-amber-400 font-mono mt-0.5">{booking.booking_id}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Offer Selected</div>
              <div className="text-sm font-bold text-white mt-0.5">{booking.offer_title || booking.offer_name || 'Standard Pass'}</div>
            </div>
            <div className="flex justify-between">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Total Passes</div>
                <div className="font-bold text-white mt-0.5">{booking.ticket_count} Passes</div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Booking Status</div>
                <div className="font-bold text-emerald-400 mt-0.5">{booking.booking_status}</div>
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500 uppercase">Registration Date</div>
              <div className="text-slate-300 mt-0.5">
                {new Date(booking.created_at).toLocaleString('en-IN')}
              </div>
            </div>
          </div>
        </div>

        {/* Financial & Email Status */}
        <div className="p-6 rounded-3xl glass-panel border border-white/10 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-amber-400 font-['Outfit']">
            Payment & Breakdown
          </h3>

          <div className="space-y-2 text-xs">
            {Boolean(booking.is_group_offer || (booking.group_discount && booking.group_discount > 0)) && (
              <div className="p-2.5 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 text-amber-300 font-semibold flex items-center justify-between text-[11px] mb-2">
                <span>🔥 {booking.offer_name || 'BUY 10, PAY FOR 9'}</span>
                <span className="text-[10px] bg-amber-500/20 px-1.5 py-0.5 rounded font-bold">1 FREE TICKET</span>
              </div>
            )}

            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Passes:</span>
              <span className="font-mono font-semibold">{booking.ticket_count} × ₹{booking.ticket_price}</span>
            </div>

            {booking.regular_amount != null && booking.group_discount != null && booking.group_discount > 0 && (
              <>
                <div className="flex justify-between text-slate-400">
                  <span>Regular Total:</span>
                  <span className="font-mono">₹{booking.regular_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between text-amber-400 font-semibold">
                  <span>Group Offer Discount:</span>
                  <span className="font-mono">-₹{booking.group_discount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              </>
            )}

            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Ticket Subtotal:</span>
              <span className="font-mono font-bold text-white">₹{(booking.ticket_subtotal ?? (booking.ticket_count * booking.ticket_price)).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>

            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Payment Fee (2%):</span>
              <span className="font-mono">₹{(booking.payment_fee ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>

            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">GST on Fee (18%):</span>
              <span className="font-mono">₹{(booking.gst_amount ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>

            <div className="pt-2 border-t border-white/10 flex justify-between items-center">
              <span className="text-xs font-bold text-white uppercase">Total Paid:</span>
              <span className="text-xl font-black text-emerald-400 font-mono">
                ₹{booking.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
            </div>

            <div className="pt-2 border-t border-white/5 space-y-1.5 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Payment Status:</span>
                <span className="font-bold text-emerald-400">{booking.payment_status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Payment Method:</span>
                <span className="font-mono text-amber-400 font-bold">{booking.payment_method || 'RAZORPAY'}</span>
              </div>

              {booking.payment_method === 'UPI_MANUAL' || booking.utr_number ? (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">UTR / Ref:</span>
                    <span className="font-mono text-white font-bold bg-black/40 px-2 py-0.5 rounded border border-white/10 select-all">
                      {booking.utr_number || 'Pending'}
                    </span>
                  </div>
                  {booking.payment_screenshot && (
                    <div className="flex justify-between items-center pt-0.5">
                      <span className="text-slate-400">Payment Proof:</span>
                      <button
                        onClick={handleViewScreenshot}
                        className="px-2 py-0.5 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 font-semibold flex items-center gap-1 cursor-pointer text-[10px]"
                      >
                        <Eye className="w-3 h-3" />
                        <span>View Screenshot</span>
                      </button>
                    </div>
                  )}
                  {booking.verified_by && (
                    <div className="flex justify-between text-slate-400 pt-0.5">
                      <span>Verified By:</span>
                      <span className="text-slate-300 font-mono">{booking.verified_by}</span>
                    </div>
                  )}
                  {booking.verified_at && (
                    <div className="flex justify-between text-slate-400">
                      <span>Verified At:</span>
                      <span className="text-slate-300">{new Date(booking.verified_at).toLocaleString('en-IN')}</span>
                    </div>
                  )}
                  {booking.rejection_reason && (
                    <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[10px]">
                      <strong>Rejection Reason:</strong> {booking.rejection_reason}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Razorpay Pay ID:</span>
                    <span className="font-mono text-[#60a5fa] font-bold">{booking.razorpay_payment_id || 'Pending'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Razorpay Order ID:</span>
                    <span className="font-mono text-slate-300">{booking.razorpay_order_id || 'Pending'}</span>
                  </div>
                  {booking.verified_at && (
                    <div className="flex justify-between text-slate-400">
                      <span>Paid / Verified At:</span>
                      <span className="text-slate-300 font-mono">{new Date(booking.verified_at).toLocaleString('en-IN')}</span>
                    </div>
                  )}
                </>
              )}
            </div>

            {(booking.booking_status === 'PAYMENT_VERIFICATION_PENDING' || booking.payment_status === 'VERIFICATION_PENDING') && (
              <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2 mt-3">
                <div className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  <span>Manual Verification Required</span>
                </div>
                <div className="text-[11px] text-slate-300 leading-relaxed">
                  Cross-verify ₹{booking.amount} with your UPI/bank app before approving.
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={handleApprovePayment}
                    disabled={approving}
                    className="flex-1 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>Approve</span>
                  </button>
                  <button
                    onClick={() => setRejectModalOpen(true)}
                    className="flex-1 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 font-bold text-xs flex items-center justify-center gap-1 cursor-pointer"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
                </div>
              </div>
            )}

            <div className="pt-3 border-t border-white/10">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500 uppercase">Customer Email</span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                    booking.email_status === 'SENT'
                      ? 'bg-emerald-500/15 text-emerald-400'
                      : booking.email_status === 'FAILED'
                      ? 'bg-rose-500/15 text-rose-400'
                      : 'bg-amber-500/15 text-amber-400'
                  }`}
                >
                  {booking.email_status}
                </span>
              </div>
              {booking.email_sent_at && (
                <div className="text-[10px] text-slate-400 mt-1">
                  Sent: {new Date(booking.email_sent_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              )}
              {booking.email_error && (
                <div className="text-[10px] text-rose-400/90 mt-1 bg-rose-500/10 p-1.5 rounded border border-rose-500/20">
                  {booking.email_error}
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500 uppercase">Owner Alert</span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                    booking.owner_notified
                      ? 'bg-emerald-500/15 text-emerald-400'
                      : 'bg-amber-500/15 text-amber-400'
                  }`}
                >
                  {booking.owner_notified ? '✓ NOTIFIED' : 'PENDING'}
                </span>
              </div>
              {booking.owner_notified_at && (
                <div className="text-[10px] text-slate-400 mt-1">
                  Sent: {new Date(booking.owner_notified_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              )}
              {booking.owner_notify_error && !booking.owner_notified && (
                <div className="text-[10px] text-amber-400/90 mt-1 bg-amber-500/10 p-1.5 rounded border border-amber-500/20">
                  {booking.owner_notify_error}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Individual Tickets Table */}
      <div className="rounded-3xl glass-panel border border-white/10 overflow-hidden shadow-xl p-6">
        <h3 className="text-base font-bold text-white mb-4 font-['Outfit'] flex items-center gap-2">
          <QrCode className="w-5 h-5 text-amber-400" />
          <span>Issued Passes ({booking.tickets.length})</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {booking.tickets.map((t, idx) => (
            <div
              key={t.ticket_id}
              className="p-5 rounded-2xl bg-black/30 border border-white/10 flex items-start justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">
                  Pass {idx + 1}
                </span>
                <div className="font-bold text-white text-sm">{t.customer_name}</div>
                <div className="text-xs font-mono text-slate-400">{t.ticket_id}</div>

                <div className="pt-2 flex items-center gap-2">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                      t.checkin_status
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'bg-emerald-500/20 text-emerald-400'
                    }`}
                  >
                    {t.checkin_status ? 'USED / CHECKED IN' : 'VALID / UNUSED'}
                  </span>
                  {t.checked_in_at && (
                    <span className="text-[10px] text-slate-400">
                      at {new Date(t.checked_in_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>

                <div className="pt-2 flex items-center gap-3 text-xs">
                  <a
                    href={`/api/tickets/${t.ticket_id}/pdf`}
                    download
                    className="text-amber-400 hover:text-amber-300 inline-flex items-center gap-1 font-semibold"
                  >
                    <Download className="w-3 h-3" />
                    <span>Download PDF</span>
                  </a>
                  {t.qr_token_raw && (
                    <Link
                      to={`/ticket/${t.qr_token_raw}`}
                      target="_blank"
                      className="text-slate-400 hover:text-white inline-flex items-center gap-1"
                    >
                      <span>Digital Pass</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>

              {t.qr_code_base64 && (
                <div className="p-1.5 bg-white rounded-xl shadow-md shrink-0">
                  <img
                    src={t.qr_code_base64.startsWith('data:') ? t.qr_code_base64 : `data:image/png;base64,${t.qr_code_base64}`}
                    alt="QR"
                    className="w-20 h-20"
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Screenshot Viewer Modal */}
      {screenshotModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="relative w-full max-w-2xl bg-[#0f0c1b] border border-white/20 rounded-3xl p-6 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  <span>Payment Screenshot Proof</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Booking <span className="font-mono text-amber-400">{booking.booking_id}</span> ({booking.customer_name})
                </p>
              </div>

              <button
                onClick={() => setScreenshotModalOpen(false)}
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
                  alt="Payment Screenshot"
                  className="max-h-[65vh] w-auto object-contain rounded-lg shadow-lg"
                />
              ) : (
                <div className="text-xs text-rose-400">Unable to load screenshot.</div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
              <div>
                UTR: <span className="font-mono text-white font-bold">{booking.utr_number || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-2">
                {screenshotUrl && (
                  <a
                    href={screenshotUrl}
                    download={`payment_${booking.booking_id}.jpg`}
                    className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold"
                  >
                    Download Image
                  </a>
                )}
                <button
                  onClick={() => setScreenshotModalOpen(false)}
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
      {rejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-[#0f0c1b] border border-white/20 rounded-3xl p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <XCircle className="w-5 h-5 text-rose-400" />
                <span>Reject Payment Submission</span>
              </h3>
              <button
                onClick={() => setRejectModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRejectPayment} className="space-y-4">
              <div className="text-xs text-slate-300">
                You are rejecting payment for{' '}
                <strong className="text-white">{booking.customer_name}</strong> (
                <span className="font-mono text-amber-400">{booking.booking_id}</span>).
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
                  onClick={() => setRejectModalOpen(false)}
                  disabled={rejecting}
                  className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={rejecting || !rejectReason.trim()}
                  className="px-5 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-md shadow-rose-500/20"
                >
                  {rejecting ? (
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
