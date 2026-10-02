import React, { useState, useEffect } from 'react';
import { ClipboardList, CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';
import { fetchStaffCheckins } from '../services/api';
import { StaffRecentCheckIn } from '../types';
import { useToast } from '../components/Toast';
import { formatDateTimeIST } from '../utils/dateUtils';

export const StaffCheckinsPage: React.FC = () => {
  const [logs, setLogs] = useState<StaffRecentCheckIn[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'ALL' | 'SUCCESS' | 'ALREADY_USED'>('ALL');
  const { error } = useToast();

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchStaffCheckins(100);
      setLogs(data);
    } catch (err: any) {
      error('Failed to load logs', err.response?.data?.detail || 'Could not fetch check-in history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredLogs = logs.filter((log) => {
    if (filter === 'ALL') return true;
    return log.result === filter;
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white font-['Outfit']">
            Gate Check-in Stream
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time audit log of scans and turnstile check-ins conducted by staff.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 p-1 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs">
            {(['ALL', 'SUCCESS', 'ALREADY_USED'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setFilter(mode)}
                className={`px-3 py-1.5 rounded-lg font-bold text-[11px] transition-colors ${
                  filter === mode
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {mode === 'ALL' ? 'All Scans' : mode === 'SUCCESS' ? 'Admitted' : 'Duplicates'}
              </button>
            ))}
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 disabled:opacity-50 transition-colors"
            title="Refresh logs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      <div className="rounded-3xl glass-panel border border-white/[0.08] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">Ticket ID</th>
                <th className="py-3 px-4">Attendee Name</th>
                <th className="py-3 px-4">Result</th>
                <th className="py-3 px-4">Check-in Time</th>
                <th className="py-3 px-4">Terminal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-500">
                    {loading ? 'Loading gate activity...' : 'No logs found matching selected filter.'}
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/[0.02]">
                    <td className="py-3.5 px-4 font-mono font-bold text-white">
                      {log.ticket_id}
                    </td>
                    <td className="py-3.5 px-4 text-slate-200 font-medium">
                      {log.customer_name}
                    </td>
                    <td className="py-3.5 px-4">
                      {log.result === 'SUCCESS' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-bold text-[10px] border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Admitted</span>
                        </span>
                      ) : log.result === 'ALREADY_USED' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-bold text-[10px] border border-amber-500/30">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Duplicate</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-400 font-bold text-[10px] border border-rose-500/30">
                          <XCircle className="w-3 h-3" />
                          <span>{log.result}</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap font-mono text-[11px]">
                      {formatDateTimeIST(log.checked_in_at, { includeSeconds: true })}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {log.device_information || 'Staff Terminal'}
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
