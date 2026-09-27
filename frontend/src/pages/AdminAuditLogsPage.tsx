import React, { useState, useEffect } from 'react';
import { ShieldAlert, RefreshCw, User, Clock, Terminal } from 'lucide-react';
import { fetchAdminAuditLogs } from '../services/api';
import { AuditLogRecord } from '../types';
import { useToast } from '../components/Toast';

export const AdminAuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const { error } = useToast();

  const loadLogs = () => {
    setLoading(true);
    fetchAdminAuditLogs(100)
      .then((data) => {
        setLogs(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching audit logs:', err);
        setLoading(false);
        error('Fetch Error', 'Failed to retrieve system audit logs.');
      });
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black text-white tracking-wide font-['Outfit'] flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
            <span>Security & System Audit Trail</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Immutable log of sensitive operations: admin authentication, bookings, check-in attempts, and setting changes.
          </p>
        </div>

        <button
          onClick={loadLogs}
          disabled={loading}
          className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/5 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-amber-400' : ''}`} />
        </button>
      </div>

      <div className="rounded-3xl glass-panel border border-white/10 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#141024] border-b border-white/10 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="py-3.5 px-4">Action</th>
                <th className="py-3.5 px-4">Entity Type</th>
                <th className="py-3.5 px-4">Entity Ref</th>
                <th className="py-3.5 px-4">Triggered By</th>
                <th className="py-3.5 px-4">IP Address</th>
                <th className="py-3.5 px-4">Audit Details</th>
                <th className="py-3.5 px-4 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300 font-mono text-[11px]">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 font-sans text-xs">
                    No audit records logged yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-4">
                      <span className="font-bold text-amber-400 font-sans text-xs">{log.action}</span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 font-sans">{log.entity_type}</td>
                    <td className="py-3.5 px-4 text-slate-200">{log.entity_id || 'N/A'}</td>
                    <td className="py-3.5 px-4 text-slate-300 font-sans">{log.user_email || 'System'}</td>
                    <td className="py-3.5 px-4 text-slate-400">{log.ip_address || '127.0.0.1'}</td>
                    <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate" title={log.details || ''}>
                      {log.details || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-right text-slate-400">
                      {new Date(log.timestamp).toLocaleDateString('en-IN', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
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
