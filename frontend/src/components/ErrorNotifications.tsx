import React from 'react';
import { AlertCircle, X, Terminal } from 'lucide-react';

interface ErrorNotificationsProps {
  error: string | null;
  onDismiss: () => void;
}

export const ErrorNotifications: React.FC<ErrorNotificationsProps> = ({ error, onDismiss }) => {
  if (!error) return null;

  const isBackendDown =
    error.includes('ECONNREFUSED') ||
    error.includes('Cannot connect') ||
    error.includes('FastAPI backend');

  return (
    <div className="bg-rose-950/70 border border-rose-800/80 rounded-xl p-4 text-rose-200 shadow-md animate-in fade-in slide-in-from-top-2 duration-200">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-rose-100 flex items-center gap-2">
              <span>Pipeline Operation Error</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300">
                Notice
              </span>
            </h4>
            <p className="text-xs text-rose-300/90 leading-relaxed break-words font-mono">
              {error}
            </p>

            {isBackendDown && (
              <div className="mt-2 text-xs bg-slate-950/80 border border-rose-900/40 p-2.5 rounded-lg text-slate-300 space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-amber-300">
                  <Terminal className="w-3.5 h-3.5" />
                  <span>Troubleshooting Hint:</span>
                </div>
                <p className="text-slate-400">
                  The Python FastAPI server runs on port 8001 supervised by Express. If unavailable, click
                  the refresh icon in the header to trigger backend health recovery.
                </p>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={onDismiss}
          className="p-1 rounded-md text-rose-400 hover:text-rose-100 hover:bg-rose-900/40 transition cursor-pointer"
          aria-label="Dismiss error notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
