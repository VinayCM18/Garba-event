import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Filter,
  Download,
  Mail,
  Eye,
  Ban,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Bell,
  CreditCard
} from 'lucide-react';
import {
  fetchAdminBookings,
  resendBookingEmail,
  resendOwnerAlert,
  cancelBooking,
  getExportCSVUrl
} from '../services/api';
import { Booking } from '../types';
import { useToast } from '../components/Toast';

export const AdminBookingsPage: React.FC = () => {
  const { success, error, info } = useToast();

  const [bookings, setBookings] = useState<Booking[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [bookingStatus, setBookingStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadBookings = (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    fetchAdminBookings({
      page,
      per_page: 15,
      search: search.trim(),
      payment_status: paymentStatus,
      booking_status: bookingStatus,
    })
      .then((res) => {
        setBookings(res.items);
        setTotal(res.total);
        setTotalPages(res.total_pages);
        if (showSpinner) setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching bookings:', err);
        if (showSpinner) {
          setLoading(false);
          error('Fetch Error', 'Failed to retrieve bookings.');
        }
      });
  };

  useEffect(() => {
    loadBookings(true);
  }, [page, paymentStatus, bookingStatus]);

  // Real-time polling every 8 seconds for automatic payment & dispatch synchronization
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadBookings(false);
    }, 8000);
    return () => clearInterval(interval);
  }, [page, paymentStatus, bookingStatus, search, autoRefresh]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadBookings(true);
  };

  const handleResendEmail = async (bookingId: string) => {
    try {
      const res = await resendBookingEmail(bookingId);
      if (res.success) {
        success('Email Sent', res.message);
        loadBookings(false);
      } else {
        error('Email Failed', res.message);
      }
    } catch (err: any) {
      error('Resend Error', 'Could not send confirmation email.');
    }
  };

  const handleResendOwnerAlert = async (bookingId: string) => {
    try {
      const res = await resendOwnerAlert(bookingId);
      if (res.success) {
        success('Owner Alert Sent', res.message);
        loadBookings(false);
      } else {
        error('Delivery Failed', res.message);
      }
    } catch (err: any) {
      error('Resend Error', 'Could not send owner alert.');
    }
  };

  const handleCancelBooking = async (bookingId: string) => {
    if (!window.confirm(`Are you sure you want to cancel booking ${bookingId}? This will invalidate all tickets.`)) {
      return;
    }
    try {
      const res = await cancelBooking(bookingId);
      if (res.success) {
        info('Booking Cancelled', res.message);
        loadBookings(false);
      }
    } catch (err: any) {
      error('Cancel Error', 'Could not cancel booking.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Top Export */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black text-white tracking-wide font-['Outfit']">
              Bookings Management
            </h2>
            <span className="inline-flex items-center gap-1 text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Sync
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Total {total} bookings registered across all channels. Auto-syncing every 8s.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={getExportCSVUrl(paymentStatus, bookingStatus)}
            download
            className="festive-button px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 shadow-md shadow-orange-500/20"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Filtered CSV</span>
          </a>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl glass-panel border border-white/10 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Global Search */}
        <form onSubmit={handleSearchSubmit} className="w-full md:max-w-md relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Booking ID, name, email, phone, ticket..."
            className="w-full pl-10 pr-20 py-2.5 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400 transition-colors"
          />
          <button
            type="submit"
            className="absolute right-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-colors"
          >
            Search
          </button>
        </form>

        {/* Filters */}
        <div className="w-full md:w-auto flex items-center gap-3">
          <select
            value={paymentStatus}
            onChange={(e) => {
              setPaymentStatus(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-amber-400"
          >
            <option value="">All Payment Statuses</option>
            <option value="PAID">PAID</option>
            <option value="PENDING">PENDING</option>
            <option value="FAILED">FAILED</option>
            <option value="REFUNDED">REFUNDED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>

          <select
            value={bookingStatus}
            onChange={(e) => {
              setBookingStatus(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-amber-400"
          >
            <option value="">All Booking Statuses</option>
            <option value="CONFIRMED">CONFIRMED</option>
            <option value="PENDING">PENDING</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>

          <button
            onClick={() => loadBookings(true)}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            title="Refresh Now"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-amber-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Bookings Table */}
      <div className="rounded-3xl glass-panel border border-white/10 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#141024] border-b border-white/10 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="py-3.5 px-4">Booking ID</th>
                <th className="py-3.5 px-4">Customer</th>
                <th className="py-3.5 px-4">Tickets</th>
                <th className="py-3.5 px-4">Regular Amount</th>
                <th className="py-3.5 px-4">Discount</th>
                <th className="py-3.5 px-4">Ticket Amount</th>
                <th className="py-3.5 px-4">Payment Fee</th>
                <th className="py-3.5 px-4">GST (18%)</th>
                <th className="py-3.5 px-4">Total Paid</th>
                <th className="py-3.5 px-4">Payment</th>
                <th className="py-3.5 px-4">Booking</th>
                <th className="py-3.5 px-4">Razorpay Payment ID</th>
                <th className="py-3.5 px-4">Created At</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {bookings.length === 0 ? (
                <tr>
                  <td colSpan={14} className="py-12 text-center text-slate-500">
                    No bookings found matching your search criteria.
                  </td>
                </tr>
              ) : (
                bookings.map((b) => {
                  const regularAmount = b.regular_amount ?? (b.ticket_count * b.ticket_price);
                  const discount = b.group_discount ?? 0.0;
                  const isGroup = Boolean(b.is_group_offer || discount > 0 || (b.ticket_count === 10 && discount > 0));
                  const offerName = b.offer_name || (isGroup ? 'BUY 10 PAY FOR 9' : null);
                  const subtotal = b.ticket_subtotal ?? (regularAmount - discount);
                  const fee = b.payment_fee ?? 0.0;
                  const gst = b.gst_amount ?? 0.0;
                  return (
                    <tr key={b.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-amber-400">
                        <Link to={`/admin/bookings/${b.booking_id}`} className="hover:underline">
                          {b.booking_id}
                        </Link>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-bold text-white">{b.customer_name}</div>
                        <div className="text-[11px] text-slate-400">{b.email}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{b.phone}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1">
                          <span className="font-mono font-bold text-white">{b.ticket_count}</span>
                          <span className="text-[10px] text-slate-400">passes</span>
                        </div>
                        {isGroup && (
                          <div className="mt-1">
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-black uppercase tracking-wider bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap">
                              🔥 {offerName}
                            </span>
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-300 whitespace-nowrap">
                        ₹{regularAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      <td className="py-3.5 px-4 font-mono whitespace-nowrap">
                        {discount > 0 ? (
                          <span className="text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                            -₹{discount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-white font-semibold whitespace-nowrap">
                        ₹{subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-400 whitespace-nowrap">
                        ₹{fee.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-400 whitespace-nowrap">
                        ₹{gst.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      <td className="py-3.5 px-4 font-mono font-bold text-emerald-400 whitespace-nowrap">
                        ₹{b.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            b.payment_status === 'PAID'
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                              : b.payment_status === 'PENDING'
                              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                              : b.payment_status === 'FAILED'
                              ? 'bg-rose-500/15 text-rose-400 border border-rose-500/20'
                              : 'bg-slate-500/15 text-slate-400 border border-slate-500/20'
                          }`}
                        >
                          {b.payment_status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            b.booking_status === 'CONFIRMED'
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                              : b.booking_status === 'PENDING'
                              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                              : 'bg-rose-500/15 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {b.booking_status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400">
                        {b.razorpay_payment_id ? (
                          <span className="text-[#60a5fa]">{b.razorpay_payment_id}</span>
                        ) : (
                          <span className="text-slate-500 italic">Pending</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                        {new Date(b.created_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            to={`/admin/bookings/${b.booking_id}`}
                            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
                            title="View Full Booking"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </Link>

                          <a
                            href={`/api/bookings/${b.booking_id}/pdf`}
                            download
                            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
                            title="Download PDF"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>

                          <button
                            onClick={() => handleResendEmail(b.booking_id)}
                            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-amber-400 hover:text-amber-300 transition-colors"
                            title="Resend Customer Email"
                          >
                            <Mail className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleResendOwnerAlert(b.booking_id)}
                            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-emerald-400 hover:text-emerald-300 transition-colors"
                            title="Resend Owner Alert"
                          >
                            <Bell className="w-3.5 h-3.5" />
                          </button>

                          {b.booking_status !== 'CANCELLED' && (
                            <button
                              onClick={() => handleCancelBooking(b.booking_id)}
                              className="p-1.5 rounded-lg bg-white/5 hover:bg-rose-500/20 text-rose-400 transition-colors"
                              title="Cancel Booking"
                            >
                              <Ban className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 bg-[#141024] border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing Page <span className="font-bold text-white">{page}</span> of{' '}
            <span className="font-bold text-white">{totalPages}</span> ({total} bookings)
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

