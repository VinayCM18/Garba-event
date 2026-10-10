import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Download,
  ShieldCheck,
  Ticket,
  CreditCard,
  QrCode,
  Users,
  Layers,
  Lock,
  AlertTriangle,
  CheckCircle2,
  Filter,
  RefreshCw,
  Info
} from 'lucide-react';
import { downloadAdminExportCsv, ExportDatasetType } from '../services/api';
import { useToast } from '../components/Toast';

export const AdminDataExportPage: React.FC = () => {
  const { success, error: toastError, info } = useToast();

  // Loading states per dataset
  const [downloading, setDownloading] = useState<Record<string, boolean>>({});

  // Bookings filters
  const [bookingPaymentStatus, setBookingPaymentStatus] = useState('');
  const [bookingStatus, setBookingStatus] = useState('');

  // Payments filters
  const [paymentStatus, setPaymentStatus] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');

  // Tickets filters
  const [ticketStatus, setTicketStatus] = useState('');
  const [ticketCheckinFilter, setTicketCheckinFilter] = useState('');

  // Checkins filters
  const [checkinResult, setCheckinResult] = useState('');

  // Users export explicit confirmation
  const [userExportConfirmed, setUserExportConfirmed] = useState(false);

  const handleExport = async (
    dataset: ExportDatasetType,
    filters: Record<string, string | boolean | undefined> = {}
  ) => {
    setDownloading((prev) => ({ ...prev, [dataset]: true }));
    info('Exporting data...', `Generating ${dataset} CSV report. Please wait.`);

    try {
      const filename = await downloadAdminExportCsv(dataset, filters);
      success('Export Complete', `Successfully downloaded ${filename}`);
    } catch (err: any) {
      console.error(`Export failed for ${dataset}:`, err);
      toastError('Export Failed', err.message || `Could not export ${dataset} records.`);
    } finally {
      setDownloading((prev) => ({ ...prev, [dataset]: false }));
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner & Security Status */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#17122b] via-[#120e24] to-[#0d0a1a] border border-[#d4af37]/30 p-6 sm:p-8 shadow-xl">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-[#d4af37]/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="p-2.5 rounded-xl bg-[#d4af37]/20 border border-[#d4af37]/40 text-[#f3e4b2]">
                <FileSpreadsheet className="w-6 h-6" />
              </span>
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-['Cinzel'] tracking-wide">
                  Secure Data Export
                </h1>
                <p className="text-xs sm:text-sm text-slate-400">
                  Export live production records to Microsoft Excel compatible CSV spreadsheets.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              <ShieldCheck className="w-4 h-4" />
              CSV Formula Injection Protected
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold">
              <Lock className="w-4 h-4" />
              Secret Keys Redacted
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              Asia/Kolkata (IST)
            </span>
          </div>
        </div>
      </div>

      {/* Info Callout */}
      <div className="rounded-xl bg-white/[0.02] border border-white/10 p-4 flex items-start gap-3 text-xs text-slate-300">
        <Info className="w-5 h-5 text-[#d4af37] shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-slate-200">
            Excel & Spreadsheet Optimization Notice
          </p>
          <p className="text-slate-400 leading-relaxed">
            All generated files include a UTF-8 Byte Order Mark (BOM) so Microsoft Excel, Apple Numbers, and Google Sheets properly recognize Unicode characters and currency symbols. In accordance with OWASP security guidelines, potential formula characters (<code className="text-amber-300">=</code>, <code className="text-amber-300">+</code>, <code className="text-amber-300">-</code>, <code className="text-amber-300">@</code>) are automatically neutralized to prevent spreadsheet execution vulnerabilities.
          </p>
        </div>
      </div>

      {/* Export Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* 1. Bookings Export Card */}
        <div className="rounded-2xl bg-[#0f0c1b] border border-white/[0.08] hover:border-[#d4af37]/40 transition-all p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[#f3e4b2]">
                <Ticket className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
                Core Sales
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-1">Bookings & Orders</h3>
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Complete customer orders, attendee pass counts, breakdown of subtotals and fees, payment statuses, and email notifications.
            </p>

            {/* Filters */}
            <div className="space-y-3 mb-6 p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                <Filter className="w-3.5 h-3.5 text-[#d4af37]" /> Filter Options
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Payment Status</label>
                <select
                  value={bookingPaymentStatus}
                  onChange={(e) => setBookingPaymentStatus(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#d4af37]/60"
                >
                  <option value="">All Payment Statuses</option>
                  <option value="PAID">PAID</option>
                  <option value="VERIFICATION_PENDING">VERIFICATION_PENDING</option>
                  <option value="PENDING">PENDING</option>
                  <option value="FAILED">FAILED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Booking Status</label>
                <select
                  value={bookingStatus}
                  onChange={(e) => setBookingStatus(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-[#d4af37]/60"
                >
                  <option value="">All Booking Statuses</option>
                  <option value="CONFIRMED">CONFIRMED</option>
                  <option value="PAYMENT_PENDING">PAYMENT_PENDING</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>
            </div>
          </div>

          <button
            onClick={() =>
              handleExport('bookings', {
                payment_status: bookingPaymentStatus,
                booking_status: bookingStatus,
              })
            }
            disabled={downloading['bookings']}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#d4af37] to-[#b38f26] text-slate-950 font-bold text-xs flex items-center justify-center gap-2 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {downloading['bookings'] ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{downloading['bookings'] ? 'Exporting...' : 'Download Bookings CSV'}</span>
          </button>
        </div>

        {/* 2. Payments Export Card */}
        <div className="rounded-2xl bg-[#0f0c1b] border border-white/[0.08] hover:border-[#d4af37]/40 transition-all p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <CreditCard className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
                Transactions
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-1">Payments & Transactions</h3>
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Financial reconciliation records including UPI UTR numbers, Razorpay payment and order IDs, amounts, and manual verification notes.
            </p>

            {/* Filters */}
            <div className="space-y-3 mb-6 p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                <Filter className="w-3.5 h-3.5 text-emerald-400" /> Filter Options
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Payment Status</label>
                <select
                  value={paymentStatus}
                  onChange={(e) => setPaymentStatus(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500/60"
                >
                  <option value="">All Statuses</option>
                  <option value="PAID">PAID</option>
                  <option value="VERIFICATION_PENDING">VERIFICATION_PENDING</option>
                  <option value="PENDING">PENDING</option>
                  <option value="FAILED">FAILED</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Payment Method</label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500/60"
                >
                  <option value="">All Methods</option>
                  <option value="RAZORPAY">Razorpay</option>
                  <option value="UPI_MANUAL">Manual UPI</option>
                </select>
              </div>
            </div>
          </div>

          <button
            onClick={() =>
              handleExport('payments', {
                payment_status: paymentStatus,
                payment_method: paymentMethod,
              })
            }
            disabled={downloading['payments']}
            className="w-full py-2.5 px-4 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold text-xs flex items-center justify-center gap-2 hover:bg-emerald-500/30 active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {downloading['payments'] ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{downloading['payments'] ? 'Exporting...' : 'Download Payments CSV'}</span>
          </button>
        </div>

        {/* 3. Tickets Export Card */}
        <div className="rounded-2xl bg-[#0f0c1b] border border-white/[0.08] hover:border-[#d4af37]/40 transition-all p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                <QrCode className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
                Attendees
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-1">Issued Entry Passes</h3>
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Individual attendee pass identifiers linked to booking IDs and gate check-in status. Raw QR tokens are strictly redacted for security.
            </p>

            {/* Filters */}
            <div className="space-y-3 mb-6 p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                <Filter className="w-3.5 h-3.5 text-purple-400" /> Filter Options
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Ticket Status</label>
                <select
                  value={ticketStatus}
                  onChange={(e) => setTicketStatus(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500/60"
                >
                  <option value="">All Statuses</option>
                  <option value="VALID">VALID</option>
                  <option value="USED">USED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Check-in Status</label>
                <select
                  value={ticketCheckinFilter}
                  onChange={(e) => setTicketCheckinFilter(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500/60"
                >
                  <option value="">All (Checked In & Unchecked)</option>
                  <option value="true">Checked In Only</option>
                  <option value="false">Not Yet Checked In</option>
                </select>
              </div>
            </div>
          </div>

          <button
            onClick={() => {
              const filters: Record<string, any> = { ticket_status: ticketStatus };
              if (ticketCheckinFilter === 'true') filters.checkin_status = true;
              if (ticketCheckinFilter === 'false') filters.checkin_status = false;
              handleExport('tickets', filters);
            }}
            disabled={downloading['tickets']}
            className="w-full py-2.5 px-4 rounded-xl bg-purple-500/20 text-purple-300 border border-purple-500/40 font-bold text-xs flex items-center justify-center gap-2 hover:bg-purple-500/30 active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {downloading['tickets'] ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{downloading['tickets'] ? 'Exporting...' : 'Download Tickets CSV'}</span>
          </button>
        </div>

        {/* 4. Check-ins Audit Card */}
        <div className="rounded-2xl bg-[#0f0c1b] border border-white/[0.08] hover:border-[#d4af37]/40 transition-all p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
                Gate Telemetry
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-1">Gate Check-in Logs</h3>
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Complete gate admission event log, including verified ticket ID, attendee name, scanning staff identity, device telemetry, and timestamp.
            </p>

            {/* Filters */}
            <div className="space-y-3 mb-6 p-3 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-300">
                <Filter className="w-3.5 h-3.5 text-cyan-400" /> Filter Options
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Scan Result</label>
                <select
                  value={checkinResult}
                  onChange={(e) => setCheckinResult(e.target.value)}
                  className="w-full bg-[#171226] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/60"
                >
                  <option value="">All Scan Results</option>
                  <option value="SUCCESS">SUCCESS</option>
                  <option value="ALREADY_USED">ALREADY_USED</option>
                  <option value="INVALID">INVALID</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>
            </div>
          </div>

          <button
            onClick={() => handleExport('checkins', { result: checkinResult })}
            disabled={downloading['checkins']}
            className="w-full py-2.5 px-4 rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold text-xs flex items-center justify-center gap-2 hover:bg-cyan-500/30 active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {downloading['checkins'] ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{downloading['checkins'] ? 'Exporting...' : 'Download Check-ins CSV'}</span>
          </button>
        </div>

        {/* 5. Offers & Inventory Card */}
        <div className="rounded-2xl bg-[#0f0c1b] border border-white/[0.08] hover:border-[#d4af37]/40 transition-all p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Layers className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
                Inventory
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-1">Offers & Inventory</h3>
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Ticket phase tiers (Early Bird, Phase 1, Phase 2), allocation capacities, sold quantities, remaining inventory counters, and active offers.
            </p>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs text-slate-400 mb-6">
              Includes real-time capacity and sold statistics across all 7 authoritative NAVRANG 2026 offers.
            </div>
          </div>

          <button
            onClick={() => handleExport('offers-inventory')}
            disabled={downloading['offers-inventory']}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 font-bold text-xs flex items-center justify-center gap-2 hover:bg-indigo-500/30 active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {downloading['offers-inventory'] ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{downloading['offers-inventory'] ? 'Exporting...' : 'Download Inventory CSV'}</span>
          </button>
        </div>

        {/* 6. Users Directory Card */}
        <div className="rounded-2xl bg-[#0f0c1b] border border-white/[0.08] hover:border-[#d4af37]/40 transition-all p-6 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
                <Users className="w-6 h-6" />
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30">
                Admin Authorized
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-1">Users & Staff Directory</h3>
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Executive and gate staff user directory with roles and last login timestamps. Passwords and hashes are strictly never exported.
            </p>

            <div className="space-y-3 mb-6 p-3 rounded-xl bg-rose-500/5 border border-rose-500/20">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span className="text-[11px] font-bold text-rose-300">Authorization Required</span>
              </div>
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-slate-300">
                <input
                  type="checkbox"
                  checked={userExportConfirmed}
                  onChange={(e) => setUserExportConfirmed(e.target.checked)}
                  className="rounded border-white/20 text-rose-500 focus:ring-rose-500/20 bg-black/40"
                />
                <span>Confirm authorization to export staff directory</span>
              </label>
            </div>
          </div>

          <button
            onClick={() => handleExport('users', { confirm: userExportConfirmed })}
            disabled={downloading['users'] || !userExportConfirmed}
            className="w-full py-2.5 px-4 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold text-xs flex items-center justify-center gap-2 hover:bg-rose-500/30 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloading['users'] ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>{downloading['users'] ? 'Exporting...' : 'Download Users CSV'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDataExportPage;
