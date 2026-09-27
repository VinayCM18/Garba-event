import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, Eye, EyeOff, KeyRound, ArrowRight, AlertCircle, ShieldCheck } from 'lucide-react';
import { adminLogin } from '../services/api';
import { useToast } from '../components/Toast';

export const ManagementLoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { success, error } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Auto redirect if already authenticated
  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const userJson = localStorage.getItem('admin_user');
    if (token && userJson) {
      try {
        const user = JSON.parse(userJson);
        if (user.role === 'SUPER_ADMIN' || user.role === 'ADMIN') {
          navigate('/admin', { replace: true });
        } else if (user.role === 'CHECKIN_STAFF' || user.role === 'STAFF') {
          navigate('/staff', { replace: true });
        }
      } catch {
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_user');
      }
    }
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      const res = await adminLogin({ email: email.trim(), password });
      success('Access Granted', `Welcome ${res.name}! Authenticated as ${res.role}.`);

      // Single Unified Login: Backend strictly dictates redirection based on role
      if (res.role === 'CHECKIN_STAFF' || res.role === 'STAFF') {
        navigate('/staff', { replace: true });
      } else {
        navigate('/admin', { replace: true });
      }
    } catch (err: any) {
      setLoading(false);
      const msg = err.response?.data?.detail || 'Invalid credentials or account inactive. Please verify with system admin.';
      setErrorMsg(msg);
      error('Login Failed', msg);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-[#06070c] relative overflow-hidden font-['Plus_Jakarta_Sans']">
      {/* Background illumination */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-gradient-to-tr from-[#d4af37]/10 via-[#1e1b4b]/15 to-transparent rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-md w-full glass-panel-gold rounded-3xl p-8 sm:p-10 border border-[#d4af37]/35 shadow-2xl relative z-10"
      >
        {/* Event / Production Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-4">
            <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-[#d4af37]/50 shadow-[0_0_20px_rgba(212,175,55,0.35)] bg-[#090a10]">
              <img
                src="/heritage_productions.jpg"
                alt="Heritage Productions"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-[0.25em] text-[#d4af37] font-['Cinzel']">
              Heritage Productions
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold bg-gradient-to-r from-white via-[#f3e4b2] to-[#d4af37] bg-clip-text text-transparent uppercase font-['Cinzel'] tracking-wider mt-0.5">
              Management Portal
            </h1>
            <p className="text-xs text-slate-400 mt-2">
              Sign in with your assigned staff or administrative credentials.
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-6 p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span className="leading-snug">{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          {/* Username / Email field */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                autoComplete="email"
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37]/50 transition-colors"
              />
            </div>
          </div>

          {/* Password field with Show/Hide toggle */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
                Password
              </label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-xs text-slate-400 hover:text-[#d4af37] flex items-center gap-1 transition-colors"
              >
                {showPassword ? (
                  <>
                    <EyeOff className="w-3.5 h-3.5" />
                    <span>Hide</span>
                  </>
                ) : (
                  <>
                    <Eye className="w-3.5 h-3.5" />
                    <span>Show</span>
                  </>
                )}
              </button>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                autoComplete="current-password"
                className="w-full pl-10 pr-10 py-3 rounded-xl bg-black/40 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37]/50 transition-colors"
              />
            </div>
          </div>

          {/* Login Button */}
          <button
            type="submit"
            disabled={loading}
            className="festive-button w-full py-3.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-[#d4af37]/25 disabled:opacity-50 transition-all mt-6"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <KeyRound className="w-4 h-4" />
                <span>Sign In to Console</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </button>
        </form>

        {/* Security watermark footer */}
        <div className="mt-8 pt-6 border-t border-white/[0.08] text-center">
          <div className="inline-flex items-center gap-1.5 text-[11px] text-slate-500 font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>Encrypted Role-Based Management Portal</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
