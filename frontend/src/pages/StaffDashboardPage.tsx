import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  QrCode,
  Users,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Search,
  RefreshCw,
  ShieldCheck,
  ArrowRight
} from 'lucide-react';
import { fetchStaffDashboard } from '../services/api';
import { StaffDashboardStats } from '../types';
import { useToast } from '../components/Toast';

export const StaffDashboardPage: React.FC = () => {
  const [stats, setStats] = useState<StaffDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { error } = useToast();

  const loadData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const data = await fetchStaffDashboard();
      setStats(data);
    } catch (err: any) {
      error('Error', err.response?.data?.detail || 'Failed to fetch gate statistics.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(), 12000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Loading Gate Console...</span>
        </div>
      </div>
    );
  }

  const expected = stats?.tickets_expected || 0;
  const checkedIn = stats?.tickets_checked_in || 0;
  const remaining = stats?.tickets_remaining || 0;
  const duplicates = stats?.duplicate_attempts || 0;
  const rate = stats?.checkin_rate_percent || 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="rounded-3xl p-6 sm:p-8 glass-panel border border-emerald-500/20 bg-gradient-to-r from-emerald-950/30 via-[#0e101c] to-[#07080f] relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Gate Security & Entry Operations</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white font-['Outfit']">
            Welcome, {stats?.staff_name || 'Staff Officer'}
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Live turnstile check-in console for NAVRANG 2026. Use high-speed optical scanning or manual booking search to verify attendees.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 relative z-10">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="px-4 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-semibold text-slate-300 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <Link
            to="/staff/scanner"
            className="festive-button px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-emerald-500/20"
          >
            <QrCode className="w-4 h-4" />
            <span>Open Scanner</span>
            <ArrowRight className="w-4 h-4 ml-0.5" />
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Checked In */}
        <div className="p-5 rounded-2xl glass-panel border border-white/[0.08]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Checked In</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-white font-mono">{checkedIn}</div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
            <span>Progress: {rate}%</span>
            <span>of {expected} total</span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-white/5 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-emerald-400 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, rate)}%` }}
            />
          </div>
        </div>

        {/* Expected Remaining */}
        <div className="p-5 rounded-2xl glass-panel border border-white/[0.08]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Expected Remaining</span>
            <div className="w-9 h-9 rounded-xl bg-amber-500/15 flex items-center justify-center text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-white font-mono">{remaining}</div>
          <div className="mt-2 text-[11px] text-slate-400">
            Guests yet to arrive at venue
          </div>
        </div>

        {/* Total Booked Tickets */}
        <div className="p-5 rounded-2xl glass-panel border border-white/[0.08]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Expected</span>
            <div className="w-9 h-9 rounded-xl bg-blue-500/15 flex items-center justify-center text-blue-400">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-white font-mono">{expected}</div>
          <div className="mt-2 text-[11px] text-slate-400">
            Confirmed admission passes
          </div>
        </div>

        {/* Duplicate Attempts */}
        <div className="p-5 rounded-2xl glass-panel border border-white/[0.08]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Duplicate Rejections</span>
            <div className="w-9 h-9 rounded-xl bg-rose-500/15 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-white font-mono">{duplicates}</div>
          <div className="mt-2 text-[11px] text-rose-300">
            Prevented re-entry attempts
          </div>
        </div>
      </div>

      {/* Quick Actions & Recent Check-in Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Launch Cards */}
        <div className="space-y-4">
          <div className="p-6 rounded-2xl glass-panel border border-white/[0.08]">
            <h2 className="text-base font-bold text-white font-['Outfit'] mb-3">
              Gate Quick Actions
            </h2>
            <div className="space-y-3">
              <Link
                to="/staff/scanner"
                className="flex items-center justify-between p-3.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-white transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <QrCode className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold">Optical Camera Scanner</div>
                    <div className="text-[10px] text-slate-400">High-speed QR recognition</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-emerald-400 group-hover:translate-x-1 transition-transform" />
              </Link>

              <Link
                to="/staff/search"
                className="flex items-center justify-between p-3.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] text-white transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/10 text-slate-300 flex items-center justify-center">
                    <Search className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold">Lookup Attendee</div>
                    <div className="text-[10px] text-slate-400">Search by name, phone, or ID</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>

        {/* Recent Check-in Logs Table */}
        <div className="lg:col-span-2 p-6 rounded-2xl glass-panel border border-white/[0.08]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-white font-['Outfit']">
                Recent Gate Activity Stream
              </h2>
              <p className="text-xs text-slate-400">Live feed of scanned tickets</p>
            </div>
            <Link
              to="/staff/checkins"
              className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold"
            >
              View all →
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.08] text-slate-400 uppercase text-[10px] tracking-wider">
                  <th className="py-2.5 px-3">Ticket ID</th>
                  <th className="py-2.5 px-3">Attendee</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Terminal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {(!stats?.recent_checkins || stats.recent_checkins.length === 0) ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No check-ins recorded yet today.
                    </td>
                  </tr>
                ) : (
                  stats.recent_checkins.slice(0, 8).map((log) => (
                    <tr key={log.id} className="hover:bg-white/[0.02]">
                      <td className="py-3 px-3 font-mono font-bold text-white">
                        {log.ticket_id}
                      </td>
                      <td className="py-3 px-3 text-slate-200">
                        {log.customer_name}
                      </td>
                      <td className="py-3 px-3">
                        {log.result === 'SUCCESS' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-bold text-[10px] border border-emerald-500/30">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Checked In</span>
                          </span>
                        ) : log.result === 'ALREADY_USED' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-bold text-[10px] border border-amber-500/30">
                            <AlertTriangle className="w-3 h-3" />
                            <span>Duplicate</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-400 font-bold text-[10px] border border-rose-500/30">
                            <span>{log.result}</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                        {log.checked_in_at
                          ? new Date(log.checked_in_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                          : 'Just now'}
                      </td>
                      <td className="py-3 px-3 text-slate-500 truncate max-w-[120px]">
                        {log.device_information || 'Scanner'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
