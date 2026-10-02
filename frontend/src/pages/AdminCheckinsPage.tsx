import React, { useState, useEffect } from 'react';
import { RefreshCw, ShieldCheck, CheckCircle2, AlertTriangle, XCircle, Search } from 'lucide-react';
import { fetchAdminCheckins } from '../services/api';
import { CheckInRecord } from '../types';
import { useToast } from '../components/Toast';
import { formatDateTimeIST } from '../utils/dateUtils';

export const AdminCheckinsPage: React.FC = () => {
  const [checkins, setCheckins] = useState<CheckInRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterResult, setFilterResult] = useState<string>('');
  const { error } = useToast();

  const loadCheckins = () => {
    setLoading(true);
    fetchAdminCheckins(100)
      .then((data) => {
        setCheckins(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching checkins:', err);
        setLoading(false);
        error('Fetch Error', 'Failed to retrieve checkin logs.');
      });
  };

  useEffect(() => {
    loadCheckins();
  }, []);

  const filtered = checkins.filter((c) => {
    if (!filterResult) return true;
    return c.result === filterResult;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-wide font-['Outfit']">
            Check-in Audit Logs
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete record of every turnstile scan attempt including duplicate rejections and invalid passes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filterResult}
            onChange={(e) => setFilterResult(e.target.value)}
            className="px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-slate-200 text-xs focus:outline-none focus:border-amber-400"
          >
            <option value="">All Scan Results</option>
            <option value="SUCCESS">SUCCESS (Admitted)</option>
            <option value="ALREADY_USED">ALREADY_USED (Duplicate Flagged)</option>
            <option value="INVALID">INVALID (Rejected)</option>
            <option value="CANCELLED">CANCELLED (Denied)</option>
          </select>

          <button
            onClick={loadCheckins}
            disabled={loading}
            className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-amber-400' : ''}`} />
          </button>
        </div>
      </div>

      <div className="rounded-3xl glass-panel border border-white/10 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#141024] border-b border-white/10 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="py-3.5 px-4">Result</th>
                <th className="py-3.5 px-4">Ticket ID</th>
                <th className="py-3.5 px-4">Booking Ref</th>
                <th className="py-3.5 px-4">Customer Name</th>
                <th className="py-3.5 px-4">Verified By Staff</th>
                <th className="py-3.5 px-4">Device Info</th>
                <th className="py-3.5 px-4 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    No check-in logs found.
                  </td>
                </tr>
              ) : (
                filtered.map((r) => (
                  <tr key={r.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                          r.result === 'SUCCESS'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : r.result === 'ALREADY_USED'
                            ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                            : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                        }`}
                      >
                        {r.result === 'SUCCESS' && <CheckCircle2 className="w-3 h-3" />}
                        {r.result === 'ALREADY_USED' && <AlertTriangle className="w-3 h-3" />}
                        {r.result === 'INVALID' && <XCircle className="w-3 h-3" />}
                        {r.result === 'CANCELLED' && <XCircle className="w-3 h-3" />}
                        <span>{r.result}</span>
                      </span>
                    </td>

                    <td className="py-3.5 px-4 font-mono font-bold text-white">
                      {r.ticket_id}
                    </td>

                    <td className="py-3.5 px-4 font-mono text-amber-400">
                      {r.booking_id}
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      {r.customer_name}
                    </td>

                    <td className="py-3.5 px-4 text-slate-300">
                      {r.staff_name || 'System Auto'}
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      {r.device_information || 'Camera Scanner'}
                    </td>

                    <td className="py-3.5 px-4 text-right text-slate-400 text-[11px]">
                      {formatDateTimeIST(r.checked_in_at, { includeSeconds: true })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
