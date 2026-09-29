import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers,
  Lock,
  Unlock,
  CheckCircle2,
  Edit3,
  Save,
  X,
  RefreshCw,
  AlertCircle,
  Tag,
  Users,
  Sparkles
} from 'lucide-react';
import { fetchAdminTicketPhases, updateAdminTicketPhase } from '../services/api';
import { TicketPhaseItem } from '../types';
import { useToast } from './Toast';

export const AdminTicketPhasesCard: React.FC = () => {
  const [phases, setPhases] = useState<TicketPhaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingCode, setUpdatingCode] = useState<string | null>(null);
  const [editingPhase, setEditingPhase] = useState<TicketPhaseItem | null>(null);
  const { success, error, info } = useToast();

  const loadPhases = async () => {
    try {
      setLoading(true);
      const data = await fetchAdminTicketPhases();
      setPhases(data);
    } catch (err: any) {
      error('Failed to Load', 'Could not fetch ticket phases from server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPhases();
  }, []);

  const handleToggleStatus = async (phase: TicketPhaseItem) => {
    const nextStatus = phase.status === 'ACTIVE' ? 'LOCKED' : 'ACTIVE';
    try {
      setUpdatingCode(phase.phase_code);
      info('Updating Phase', `Setting ${phase.name} to ${nextStatus}...`);
      await updateAdminTicketPhase(phase.phase_code, { status: nextStatus });
      success('Phase Updated', `${phase.name} is now ${nextStatus}.`);
      await loadPhases();
    } catch (err: any) {
      error('Update Failed', err.response?.data?.detail || 'Failed to update phase status.');
    } finally {
      setUpdatingCode(null);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingPhase) return;
    try {
      setUpdatingCode(editingPhase.phase_code);
      await updateAdminTicketPhase(editingPhase.phase_code, {
        name: editingPhase.name,
        price: Number(editingPhase.price),
        total_inventory: Number(editingPhase.total_inventory),
        badge_text: editingPhase.badge_text,
        description: editingPhase.description,
        group_offer_eligible: editingPhase.group_offer_eligible,
        status: editingPhase.status
      });
      success('Saved', `Configuration for ${editingPhase.name} saved.`);
      setEditingPhase(null);
      await loadPhases();
    } catch (err: any) {
      error('Save Failed', err.response?.data?.detail || 'Could not save phase changes.');
    } finally {
      setUpdatingCode(null);
    }
  };

  return (
    <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-white/10 shadow-2xl relative overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[#d4af37] via-[#aa8024] to-[#795914] flex items-center justify-center text-[#090710] font-black shadow-lg shadow-[#d4af37]/20">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg sm:text-xl font-black text-white font-['Outfit'] tracking-wide flex items-center gap-2">
              Ticket Phase Management
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#d4af37]/20 text-[#f3e4b2] border border-[#d4af37]/35 uppercase tracking-wider font-mono">
                NAVRANG 2026
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Control live ticket availability, pricing tiers, lock/unlock states, and inventory allocations.
            </p>
          </div>
        </div>

        <button
          onClick={loadPhases}
          disabled={loading}
          className="self-start sm:self-center px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 flex items-center gap-2 border border-white/10 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Phases</span>
        </button>
      </div>

      {loading && phases.length === 0 ? (
        <div className="py-12 text-center text-xs text-slate-400">
          <div className="w-6 h-6 border-2 border-[#d4af37] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          Loading ticket phase configurations...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-6">
          {phases.map((phase) => {
            const isActive = phase.status === 'ACTIVE';
            const isLocked = phase.status === 'LOCKED';
            const isSoldOut = phase.status === 'SOLD_OUT';
            const isBusy = updatingCode === phase.phase_code;

            return (
              <motion.div
                key={phase.phase_code}
                layout
                className={`rounded-2xl p-5 border transition-all relative flex flex-col justify-between ${
                  isActive
                    ? 'bg-gradient-to-b from-[#1b1528] to-[#120d20] border-[#d4af37]/60 shadow-[0_0_25px_rgba(212,175,55,0.15)] ring-1 ring-[#d4af37]/40'
                    : 'bg-[#0f0c1b]/80 border-white/10 hover:border-white/20'
                }`}
              >
                <div>
                  {/* Top Badge & Status */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span
                      className={`text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full border flex items-center gap-1.5 ${
                        isActive
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : isLocked
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                      }`}
                    >
                      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
                      {isLocked && <Lock className="w-3 h-3" />}
                      {phase.status}
                    </span>

                    {phase.badge_text && (
                      <span className="text-[10px] font-extrabold text-[#f3e4b2] uppercase tracking-wider bg-white/5 px-2 py-0.5 rounded-md border border-white/10">
                        {phase.badge_text}
                      </span>
                    )}
                  </div>

                  {/* Phase Title & Price */}
                  <div className="mb-4">
                    <h4 className="text-lg font-black text-white uppercase font-['Cinzel'] tracking-wide">
                      {phase.name}
                    </h4>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-[#f7e8c3] to-[#d4af37] font-mono">
                        ₹{Number(phase.price).toLocaleString('en-IN')}
                      </span>
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">
                        {phase.tax_included ? 'Taxes Included' : '+ Taxes'}
                      </span>
                    </div>
                    {phase.description && (
                      <p className="text-[11px] text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                        {phase.description}
                      </p>
                    )}
                  </div>

                  {/* Inventory Metrics Grid */}
                  <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-black/40 border border-white/5 mb-4 text-center">
                    <div>
                      <span className="text-[9px] text-slate-400 uppercase font-bold block">Capacity</span>
                      <span className="text-xs font-mono font-bold text-white mt-0.5 block">
                        {phase.total_inventory}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-400 uppercase font-bold block">Sold</span>
                      <span className="text-xs font-mono font-bold text-emerald-400 mt-0.5 block">
                        {phase.sold_count}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-400 uppercase font-bold block">Left</span>
                      <span className="text-xs font-mono font-bold text-[#f3e4b2] mt-0.5 block">
                        {phase.remaining_tickets}
                      </span>
                    </div>
                  </div>

                  {phase.group_offer_eligible && (
                    <div className="mb-4 inline-flex items-center gap-1.5 text-[10px] font-bold text-emerald-300 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                      <Sparkles className="w-3 h-3 text-emerald-400" />
                      Eligible for Group Offer (Buy 10, Pay 9)
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="pt-3 border-t border-white/10 flex items-center gap-2">
                  <button
                    onClick={() => handleToggleStatus(phase)}
                    disabled={isBusy}
                    className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-50 ${
                      isActive
                        ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30'
                        : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30'
                    }`}
                  >
                    {isActive ? (
                      <>
                        <Lock className="w-3.5 h-3.5" />
                        <span>Lock Phase</span>
                      </>
                    ) : (
                      <>
                        <Unlock className="w-3.5 h-3.5" />
                        <span>Activate Phase</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setEditingPhase({ ...phase })}
                    disabled={isBusy}
                    className="py-2 px-3 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1 border border-white/10 transition-colors"
                    title="Edit Price & Details"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Edit</span>
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Edit Phase Modal */}
      <AnimatePresence>
        {editingPhase && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-panel p-6 sm:p-7 rounded-3xl border border-[#d4af37]/40 max-w-lg w-full shadow-2xl relative bg-[#130f20]"
            >
              <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-5">
                <div>
                  <h4 className="text-lg font-black text-white font-['Outfit']">
                    Edit {editingPhase.name}
                  </h4>
                  <span className="text-[10px] text-slate-400 font-mono uppercase">
                    Phase Code: {editingPhase.phase_code}
                  </span>
                </div>
                <button
                  onClick={() => setEditingPhase(null)}
                  className="p-1.5 rounded-xl hover:bg-white/10 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-bold uppercase tracking-wider mb-1.5">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={editingPhase.name}
                    onChange={(e) => setEditingPhase({ ...editingPhase, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white focus:outline-none focus:border-[#d4af37]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-bold uppercase tracking-wider mb-1.5">
                      Base Price (₹)
                    </label>
                    <input
                      type="number"
                      value={editingPhase.price}
                      onChange={(e) => setEditingPhase({ ...editingPhase, price: Number(e.target.value) })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white font-mono focus:outline-none focus:border-[#d4af37]"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-300 font-bold uppercase tracking-wider mb-1.5">
                      Total Inventory
                    </label>
                    <input
                      type="number"
                      value={editingPhase.total_inventory}
                      onChange={(e) =>
                        setEditingPhase({ ...editingPhase, total_inventory: Number(e.target.value) })
                      }
                      className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white font-mono focus:outline-none focus:border-[#d4af37]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-bold uppercase tracking-wider mb-1.5">
                    Badge Text (e.g. "AVAILABLE NOW" or "COMING SOON")
                  </label>
                  <input
                    type="text"
                    value={editingPhase.badge_text || ''}
                    onChange={(e) => setEditingPhase({ ...editingPhase, badge_text: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/10 text-white focus:outline-none focus:border-[#d4af37]"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold uppercase tracking-wider mb-1.5">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    value={editingPhase.description || ''}
                    onChange={(e) => setEditingPhase({ ...editingPhase, description: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-black/50 border border-white/10 text-white focus:outline-none focus:border-[#d4af37]"
                  />
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <input
                    type="checkbox"
                    id="edit_group_offer"
                    checked={editingPhase.group_offer_eligible}
                    onChange={(e) =>
                      setEditingPhase({ ...editingPhase, group_offer_eligible: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-[#d4af37] focus:ring-0 cursor-pointer accent-[#d4af37]"
                  />
                  <label htmlFor="edit_group_offer" className="text-slate-300 font-medium cursor-pointer">
                    Eligible for "Buy 10, Pay for 9" group promotion
                  </label>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setEditingPhase(null)}
                  className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveEdit}
                  disabled={updatingCode === editingPhase.phase_code}
                  className="festive-button px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Phase</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
