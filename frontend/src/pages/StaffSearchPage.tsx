import React, { useState } from 'react';
import { Search, CheckCircle2, AlertTriangle, XCircle, ArrowRight, RefreshCw, UserCheck } from 'lucide-react';
import { staffSearchTickets, staffCheckInTicket } from '../services/api';
import { StaffSearchItem } from '../types';
import { useToast } from '../components/Toast';

export const StaffSearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StaffSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [checkingInId, setCheckingInId] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const { success, error, warning } = useToast();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || query.trim().length < 2) {
      warning('Search query too short', 'Please enter at least 2 characters.');
      return;
    }

    setLoading(true);
    setSearched(true);
    try {
      const data = await staffSearchTickets(query.trim());
      setResults(data);
    } catch (err: any) {
      error('Search failed', err.response?.data?.detail || 'Failed to search attendee database.');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async (ticketId: string, customerName: string) => {
    setCheckingInId(ticketId);
    try {
      await staffCheckInTicket({
        qr_token: ticketId,
        device_information: 'Staff Lookup Terminal',
        notes: `Checked in via manual lookup by staff`
      });

      success('Check-in Successful', `${customerName} admitted!`);
      // Update local state
      setResults((prev) =>
        prev.map((t) =>
          t.ticket_id === ticketId
            ? { ...t, checkin_status: true, ticket_status: 'USED', checked_in_at: new Date().toISOString() }
            : t
        )
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to check in ticket.';
      error('Check-in Rejected', msg);
    } finally {
      setCheckingInId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-white font-['Outfit']">
          Attendee & Booking Search
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Look up attendees by Ticket ID, Booking ID, Phone number, or Customer Name for manual admission.
        </p>
      </div>

      {/* Search Input Bar */}
      <form onSubmit={handleSearch} className="max-w-2xl flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by Ticket ID (GN26-TKT-...), Booking ID, Name, or Phone..."
            className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-400 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="festive-button px-6 py-3.5 rounded-2xl text-xs font-bold uppercase tracking-wider disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          <span>Search</span>
        </button>
      </form>

      {/* Results Section */}
      <div className="rounded-3xl glass-panel border border-white/[0.08] overflow-hidden">
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
          <div className="text-xs font-bold text-white uppercase tracking-wider">
            Matching Attendees {searched && `(${results.length} found)`}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">Ticket ID</th>
                <th className="py-3 px-4">Attendee Name</th>
                <th className="py-3 px-4">Booking Ref</th>
                <th className="py-3 px-4">Phone</th>
                <th className="py-3 px-4">Gate Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {results.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 text-xs">
                    {searched
                      ? `No tickets found matching "${query}". Try searching by numeric digits or partial name.`
                      : 'Type a query above to search tickets.'}
                  </td>
                </tr>
              ) : (
                results.map((ticket) => (
                  <tr key={ticket.ticket_id} className="hover:bg-white/[0.02]">
                    <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                      {ticket.ticket_id}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-white">
                      {ticket.customer_name}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {ticket.booking_id}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {ticket.phone || 'N/A'}
                    </td>
                    <td className="py-3.5 px-4">
                      {ticket.checkin_status ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-400 font-bold text-[10px] border border-amber-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Checked In</span>
                        </span>
                      ) : ticket.ticket_status === 'VALID' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 font-bold text-[10px] border border-emerald-500/30">
                          <UserCheck className="w-3 h-3" />
                          <span>Valid • Ready</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-400 font-bold text-[10px] border border-rose-500/30">
                          <XCircle className="w-3 h-3" />
                          <span>{ticket.ticket_status}</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {!ticket.checkin_status && ticket.ticket_status === 'VALID' ? (
                        <button
                          onClick={() => handleCheckIn(ticket.ticket_id, ticket.customer_name)}
                          disabled={checkingInId === ticket.ticket_id}
                          className="px-3.5 py-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold tracking-wider uppercase transition-all disabled:opacity-50 inline-flex items-center gap-1.5"
                        >
                          {checkingInId === ticket.ticket_id ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3" />
                          )}
                          <span>Admit</span>
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-500 font-medium">
                          {ticket.checkin_status ? 'Admitted' : 'Denied'}
                        </span>
                      )}
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
