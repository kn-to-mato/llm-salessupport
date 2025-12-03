import { Bot, Loader2 } from 'lucide-react';

export function LoadingIndicator() {
  return (
    <div className="flex gap-4 animate-slide-up">
      <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
        <Bot className="w-5 h-5 text-white" />
      </div>
      <div className="glass-panel rounded-2xl px-5 py-4 flex items-center gap-3">
        <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
        <span className="text-dark-400 animate-pulse-soft">
          考え中...
        </span>
      </div>
    </div>
  );
}

