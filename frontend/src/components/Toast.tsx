import React, { createContext, useContext, useState, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'warning' | 'error' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextType {
  showToast: (type: ToastType, title: string, message?: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const showToast = (type: ToastType, title: string, message?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

  const success = (title: string, message?: string) => showToast('success', title, message);
  const error = (title: string, message?: string) => showToast('error', title, message);
  const warning = (title: string, message?: string) => showToast('warning', title, message);
  const info = (title: string, message?: string) => showToast('info', title, message);

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-md w-full px-4 pointer-events-none">
        <AnimatePresence>
          {toasts.map((toast) => {
            const icons = {
              success: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />,
              warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
              error: <XCircle className="w-5 h-5 text-rose-400 shrink-0" />,
              info: <Info className="w-5 h-5 text-sky-400 shrink-0" />,
            };

            const borders = {
              success: 'border-emerald-500/40 bg-[#0f1f18]/90 text-emerald-100',
              warning: 'border-amber-500/40 bg-[#241a0b]/90 text-amber-100',
              error: 'border-rose-500/40 bg-[#250e14]/90 text-rose-100',
              info: 'border-sky-500/40 bg-[#0b1b28]/90 text-sky-100',
            };

            return (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-xl backdrop-blur-md ${borders[toast.type]}`}
              >
                {icons[toast.type]}
                <div className="flex-1 text-sm">
                  <div className="font-semibold text-white">{toast.title}</div>
                  {toast.message && <div className="text-xs mt-0.5 opacity-90">{toast.message}</div>}
                </div>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="opacity-60 hover:opacity-100 transition-opacity p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
