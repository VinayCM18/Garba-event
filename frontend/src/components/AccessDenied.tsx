import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldAlert, ArrowRight, Home } from 'lucide-react';

interface AccessDeniedProps {
  redirectPath?: string;
  autoRedirectMs?: number;
}

export const AccessDenied: React.FC<AccessDeniedProps> = ({
  redirectPath = '/staff',
  autoRedirectMs = 3500
}) => {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate(redirectPath, { replace: true });
    }, autoRedirectMs);
    return () => clearTimeout(timer);
  }, [navigate, redirectPath, autoRedirectMs]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 font-['Plus_Jakarta_Sans']">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md w-full glass-panel border border-rose-500/30 rounded-3xl p-8 text-center shadow-2xl"
      >
        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto mb-5 text-rose-400">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-black text-white font-['Outfit'] mb-2">
          Access Denied
        </h2>
        <p className="text-xs text-slate-300 leading-relaxed mb-6">
          You do not have administrative privileges to access this area. Staff personnel are restricted to ticket scanning, attendee verification, and check-in logs.
        </p>

        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-[11px] text-slate-400 mb-6">
          Redirecting you to the <strong>Staff Dashboard</strong> in {Math.round(autoRedirectMs / 1000)} seconds...
        </div>

        <button
          onClick={() => navigate(redirectPath, { replace: true })}
          className="festive-button w-full py-3 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2"
        >
          <span>Return to Staff Dashboard</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </motion.div>
    </div>
  );
};
