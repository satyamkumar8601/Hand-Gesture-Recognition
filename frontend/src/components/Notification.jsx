import React from 'react';
import { CheckCircle2, AlertCircle, Info } from 'lucide-react';
import { useApp } from '../context/AppContext';

export const Notification = () => {
  const { notifications } = useApp();

  if (!notifications.length) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {notifications.map((n) => {
        const isSuccess = n.type === 'success';
        const isError = n.type === 'error';
        const Icon = isSuccess ? CheckCircle2 : isError ? AlertCircle : Info;

        return (
          <div
            key={n.id}
            className={`pointer-events-auto flex items-center gap-3 p-3.5 rounded-xl border backdrop-blur-xl shadow-xl transition-all duration-300 animate-in fade-in slide-in-from-bottom-2 ${
              isSuccess
                ? 'bg-emerald-950/80 border-emerald-500/40 text-emerald-200'
                : isError
                ? 'bg-rose-950/80 border-rose-500/40 text-rose-200'
                : 'bg-slate-900/80 border-slate-700/80 text-slate-200'
            }`}
          >
            <Icon className={`h-5 w-5 flex-shrink-0 ${isSuccess ? 'text-accent' : isError ? 'text-rose-400' : 'text-primary'}`} />
            <span className="text-xs font-medium">{n.message}</span>
          </div>
        );
      })}
    </div>
  );
};
