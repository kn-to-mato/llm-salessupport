import { Briefcase, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

interface HeaderProps {
  onReset: () => void;
  sessionId?: string;
}

export function Header({ onReset, sessionId }: HeaderProps) {
  return (
    <header className="glass-panel border-b border-dark-700/50">
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center glow-primary">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold gradient-text">
                営業出張サポートAI
              </h1>
              <p className="text-xs text-dark-400">
                出張計画をAIがサポートします
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            {sessionId && (
              <span className="text-xs text-dark-500 font-mono hidden sm:block">
                Session: {sessionId.slice(0, 8)}...
              </span>
            )}
            <button
              onClick={onReset}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
                "bg-dark-800 text-dark-300 border border-dark-700",
                "hover:bg-dark-700 hover:text-dark-100 hover:border-dark-600",
                "transition-all duration-200"
              )}
            >
              <RotateCcw className="w-4 h-4" />
              <span className="hidden sm:inline">新規会話</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
