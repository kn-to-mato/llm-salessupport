import { Briefcase, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

interface HeaderProps {
  onReset: () => void;
  sessionId?: string;
}

// バックエンドの種類を取得
const BACKEND_TYPE = import.meta.env.VITE_BACKEND || 'python';
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || '';

const backendInfo = {
  python: {
    label: 'Python + LangChain',
    color: 'from-blue-500 to-yellow-500',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    icon: '🐍',
  },
  pythonVertex: {
    label: 'Python + Vertex AI',
    color: 'from-blue-500 to-emerald-500',
    textColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    icon: '🧠',
  },
  typescript: {
    label: 'TypeScript + Mastra',
    color: 'from-blue-400 to-cyan-400',
    textColor: 'text-cyan-400',
    borderColor: 'border-cyan-500/30',
    icon: '🔷',
  },
};

export function Header({ onReset, sessionId }: HeaderProps) {
  const looksLikeVertexBackend =
    BACKEND_TYPE === 'python' &&
    !!BACKEND_URL &&
    /(a\.run\.app|backend-vertex|vertex)/i.test(BACKEND_URL);

  const backendKey = looksLikeVertexBackend ? 'pythonVertex' : BACKEND_TYPE;
  const backend =
    backendInfo[backendKey as keyof typeof backendInfo] ||
    backendInfo.python;

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
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold gradient-text">
                  営業出張サポートAI
                </h1>
                {/* Backend Badge */}
                <span className={clsx(
                  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium",
                  "bg-dark-800/80 border",
                  backend.borderColor,
                  backend.textColor
                )}>
                  <span>{backend.icon}</span>
                  <span className="hidden sm:inline">{backend.label}</span>
                </span>
              </div>
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

