import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, Mail, Lock, ArrowRight, Sparkles, KeyRound, AlertCircle } from 'lucide-react';
import { adminLogin } from '../services/api';
import { useToast } from '../components/Toast';

export const AdminLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { success, error } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      const res = await adminLogin({ email: email.trim(), password });
      success('Welcome back!', `Logged in as ${res.name} (${res.role})`);
      if (res.role === 'CHECKIN_STAFF') {
        navigate('/admin/scanner');
      } else {
        navigate('/admin');
      }
    } catch (err: any) {
      setLoading(false);
      const msg = err.response?.data?.detail || 'Invalid email or password. Please try again.';
      setErrorMsg(msg);
      error('Login Failed', msg);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-[#06070c] relative overflow-hidden font-['Plus_Jakarta_Sans']">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-gradient-to-tr from-[#d4af37]/10 via-[#1e1b4b]/15 to-transparent rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="max-w-md w-full glass-panel-gold rounded-3xl p-8 border border-[#d4af37]/30 shadow-2xl relative z-10"
      >
        {/* Brand */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2.5 mb-3 group">
            <div className="w-10 h-10 rounded-full overflow-hidden border border-[#d4af37]/50 shadow-lg shadow-[#d4af37]/25 bg-[#090a10]">
              <img
                src="/heritage_productions.jpg"
                alt="Heritage Productions"
                className="w-full h-full object-cover"
              />
            </div>
            <span className="text-xl font-extrabold tracking-[0.1em] bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent uppercase font-['Cinzel']">
              NAVRANG 2026
            </span>
          </Link>
          <h2 className="text-2xl font-bold text-white font-['Cinzel'] tracking-wide">
            Executive & Scanner Portal
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Sign in to access event analytics, manage guest lists, and operate the live optical QR turnstiles.
          </p>
        </div>

        {errorMsg && (
          <div className="mb-6 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="festive-button w-full py-3.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-orange-500/25 disabled:opacity-50 transition-all"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <KeyRound className="w-4 h-4" />
                <span>Secure Sign In</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-center pt-6 border-t border-white/10">
          <Link to="/" className="text-xs text-slate-400 hover:text-white transition-colors">
            ← Back to Public Website
          </Link>
        </div>
      </motion.div>
    </div>
  );
};
