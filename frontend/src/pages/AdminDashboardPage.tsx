import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  Ticket,
  Users,
  CheckCircle2,
  DollarSign,
  QrCode,
  ArrowUpRight,
  Download,
  Calendar,
  Layers,
  Sparkles,
  RefreshCw,
  Bell,
  ShieldCheck
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts';
import {
  fetchDashboardAnalytics,
  fetchAdminCheckins,
  fetchRecentNotifications,
  fetchPendingPaymentVerifications,
  getExportCSVUrl
} from '../services/api';
import { DashboardAnalytics, CheckInRecord, RecentNotification } from '../types';
import { useToast } from '../components/Toast';

export const AdminDashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [checkins, setCheckins] = useState<CheckInRecord[]>([]);
  const [recentBookings, setRecentBookings] = useState<RecentNotification[]>([]);
  const [pendingVerifications, setPendingVerifications] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const { error } = useToast();

  const loadData = (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    Promise.all([
      fetchDashboardAnalytics(),
      fetchAdminCheckins(6),
      fetchRecentNotifications(6),
      fetchPendingPaymentVerifications('VERIFICATION_PENDING').catch(() => [])
    ])
      .then(([analyticsRes, checkinsRes, bookingsRes, verificationsRes]) => {
        setData(analyticsRes);
        setCheckins(checkinsRes);
        setRecentBookings(bookingsRes);
        setPendingVerifications(Array.isArray(verificationsRes) ? verificationsRes.length : 0);
        if (showSpinner) setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching dashboard stats:', err);
        if (showSpinner) {
          setLoading(false);
          error('Dashboard Error', 'Could not refresh analytics data.');
        }
      });
  };

  useEffect(() => {
    loadData(true);
    // Real-time polling every 8 seconds for dashboard synchronization
    const interval = setInterval(() => {
      loadData(false);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const stats = data?.stats;


  return (
    <div className="space-y-8">
      {/* Top Banner & Quick Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-wide font-['Outfit']">
            Event Performance Overview
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time ticketing metrics, revenue progression, and gate check-in status.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={loading}
            className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5 transition-colors"
            title="Refresh statistics"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-amber-400' : ''}`} />
          </button>

          <a
            href={getExportCSVUrl()}
            download
            className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5 text-xs font-semibold flex items-center gap-2 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </a>

          <Link
            to="/admin/scanner"
            className="festive-button px-5 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg shadow-orange-500/20"
          >
            <QrCode className="w-4 h-4" />
            <span>Launch Camera Scanner</span>
          </Link>
        </div>
      </div>

      {/* Pending Payment Verification Banner */}
      {pendingVerifications > 0 && (
        <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-500/20 via-orange-500/15 to-transparent border border-amber-500/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-lg shadow-amber-500/10 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-300 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>{pendingVerifications} Payment Verification{pendingVerifications > 1 ? 's' : ''} Awaiting Approval</span>
                <span className="text-[10px] bg-amber-500 text-slate-950 font-bold px-2 py-0.5 rounded-full font-mono">
                  ACTION REQUIRED
                </span>
              </div>
              <div className="text-xs text-slate-300 mt-0.5">
                Customers have submitted UTR transaction numbers and payment screenshots via manual UPI.
              </div>
            </div>
          </div>

          <Link
            to="/admin/verification"
            className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md shadow-amber-500/20 transition-all shrink-0 cursor-pointer"
          >
            <span>Review &amp; Approve Submissions</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* TOTAL BOOKINGS */}
        <div className="p-5 rounded-2xl glass-panel border border-white/10 hover:border-[#d4af37]/35 transition-all shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-['Outfit']">TOTAL BOOKINGS</span>
            <div className="w-8 h-8 rounded-xl bg-[#d4af37]/15 text-[#f3e4b2] flex items-center justify-center">
              <Ticket className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-black text-white font-mono">
            {stats?.total_bookings ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {stats?.tickets_sold ?? 0} tickets sold
          </div>
        </div>

        {/* PAYMENTS */}
        <div className="p-5 rounded-2xl glass-panel border border-white/10 hover:border-amber-500/35 transition-all shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-['Outfit']">PAYMENTS</span>
            <div className="w-8 h-8 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-black text-amber-400 font-mono">
            {stats?.total_bookings ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {pendingVerifications > 0 ? `${pendingVerifications} verification pending` : 'All verified'}
          </div>
        </div>

        {/* REVENUE */}
        <div className="p-5 rounded-2xl glass-panel border border-white/10 hover:border-emerald-500/35 transition-all shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-['Outfit']">REVENUE</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-black text-emerald-400 font-mono">
            ₹{(stats?.revenue ?? 0).toLocaleString('en-IN')}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            gross verified
          </div>
        </div>

        {/* CHECK-INS */}
        <div className="p-5 rounded-2xl glass-panel border border-white/10 hover:border-purple-500/35 transition-all shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-['Outfit']">CHECK-INS</span>
            <div className="w-8 h-8 rounded-xl bg-purple-500/15 text-purple-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-black text-purple-400 font-mono">
            {stats?.checked_in ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            {stats?.checkin_rate_percentage ?? 0}% checked in
          </div>
        </div>

        {/* Remaining Capacity */}
        <div className="p-5 rounded-2xl glass-panel border border-white/10 hover:border-[#d4af37]/30 transition-all shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Remaining</span>
            <div className="w-8 h-8 rounded-xl bg-[#d4af37]/15 text-[#f3e4b2] flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 text-2xl sm:text-3xl font-black text-[#f3e4b2] font-mono">
            {stats?.remaining_tickets ?? 0}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">
            passes left
          </div>
        </div>
      </div>

      {/* Interactive Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Revenue Trend Area Chart */}
        <div className="lg:col-span-8 p-6 rounded-3xl glass-panel border border-white/10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-bold text-white font-['Outfit'] flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-400" />
                <span>Revenue Progression (Last 7 Days)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Daily gross collections from ticket bookings</p>
            </div>
            <span className="text-xs font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
              Live INR
            </span>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data?.sales_trend || []}>
                <defs>
                  <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#26213b" vertical={false} />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `₹${v}`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#161226',
                    borderColor: 'rgba(245, 158, 11, 0.3)',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#fff',
                  }}
                  formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Revenue']}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#f59e0b"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorRev)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tickets Sold by Day Bar Chart */}
        <div className="lg:col-span-4 p-6 rounded-3xl glass-panel border border-white/10 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-white font-['Outfit'] flex items-center gap-2">
              <Ticket className="w-4 h-4 text-orange-400" />
              <span>Tickets Sold Daily</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Tickets booked per day</p>
          </div>

          <div className="h-60 w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.sales_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#26213b" vertical={false} />
                <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#161226',
                    borderColor: 'rgba(234, 88, 12, 0.3)',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#fff',
                  }}
                />
                <Bar dataKey="tickets" fill="#ea580c" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="pt-4 border-t border-white/5 text-center">
            <Link
              to="/admin/bookings"
              className="text-xs font-semibold text-amber-400 hover:text-amber-300 inline-flex items-center gap-1"
            >
              <span>View All Detailed Bookings</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* 2-Column Responsive Feed: Live Ticket Bookings & Entry Scans */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Booking Notifications & Owner Alerts */}
        <div className="p-6 rounded-3xl glass-panel border border-amber-500/20 bg-gradient-to-b from-amber-500/[0.03] to-transparent">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-base font-bold text-white font-['Outfit'] flex items-center gap-2">
                <Bell className="w-4 h-4 text-amber-400" />
                <span>Live Booking Alerts</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Real-time attendee bookings and owner alerts</p>
            </div>

            <Link
              to="/admin/bookings"
              className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {recentBookings.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">
              No recent bookings yet. Ready to receive attendee orders!
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {recentBookings.map((b) => (
                <div key={b.id} className="py-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex flex-col items-center justify-center font-bold text-amber-400 shrink-0">
                      <span className="text-xs leading-none">{b.ticket_count}</span>
                      <span className="text-[8px] uppercase tracking-tighter opacity-80">Tkts</span>
                    </div>
                    <div>
                      <div className="font-bold text-white flex items-center gap-2">
                        <span>{b.customer_name}</span>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                          ₹{b.amount.toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {b.booking_id} • {b.phone}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="flex items-center gap-1.5 justify-end">
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          b.email_status === 'SENT'
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : 'bg-amber-500/15 text-amber-400'
                        }`}
                      >
                        Email {b.email_status === 'SENT' ? '✓' : b.email_status}
                      </span>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          b.owner_notified
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : 'bg-amber-500/15 text-amber-400'
                        }`}
                      >
                        Owner {b.owner_notified ? '✓' : 'Pending'}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">
                      {new Date(b.created_at).toLocaleTimeString('en-IN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live Recent Check-in Activity Feed */}
        <div className="p-6 rounded-3xl glass-panel border border-white/10">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-base font-bold text-white font-['Outfit'] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Recent Entry Gate Scans</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Real-time turnstile validation events</p>
            </div>

            <Link
              to="/admin/checkins"
              className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1"
            >
              <span>View Full Check-in Log</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {checkins.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">
              No gate check-in scans recorded yet. Ready to scan passes!
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {checkins.map((item) => (
                <div key={item.id} className="py-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-[10px] ${
                        item.result === 'SUCCESS'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : item.result === 'ALREADY_USED'
                          ? 'bg-amber-500/20 text-amber-400'
                          : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      {item.result === 'SUCCESS' ? '✓' : '!'}
                    </div>
                    <div>
                      <div className="font-bold text-white">{item.customer_name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.ticket_id} • Booking #{item.booking_id}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                        item.result === 'SUCCESS'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : item.result === 'ALREADY_USED'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-rose-500/10 text-rose-400'
                      }`}
                    >
                      {item.result}
                    </span>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {new Date(item.checked_in_at).toLocaleTimeString('en-IN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
