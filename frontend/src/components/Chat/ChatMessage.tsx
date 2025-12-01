import { useMemo } from 'react';
import { User, Bot } from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage as ChatMessageType, TravelPlan } from '../../types';
import { PlanCard } from '../PlanCard';
import { ApplicationDataCard } from '../ApplicationDataCard';

interface ChatMessageProps {
  message: ChatMessageType;
  onSelectPlan?: (plan: TravelPlan) => void;
}

export function ChatMessage({ message, onSelectPlan }: ChatMessageProps) {
  const isUser = message.role === 'user';
  
  const formattedTime = useMemo(() => {
    return message.timestamp.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }, [message.timestamp]);

  return (
    <div
      className={clsx(
        "flex gap-4 animate-slide-up",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          "flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center",
          isUser
            ? "bg-gradient-to-br from-accent-500 to-accent-600"
            : "bg-gradient-to-br from-primary-500 to-primary-600"
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Content */}
      <div
        className={clsx(
          "flex-1 max-w-[80%]",
          isUser ? "items-end" : "items-start"
        )}
      >
        <div
          className={clsx(
            "rounded-2xl px-5 py-4",
            isUser
              ? "bg-gradient-to-br from-accent-500/20 to-accent-600/10 border border-accent-500/30"
              : "glass-panel"
          )}
        >
          {/* Text content */}
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>

          {/* Plans */}
          {message.plans && message.plans.length > 0 && (
            <div className="mt-4 space-y-4">
              <div className="text-sm font-medium text-primary-400 mb-2">
                出張プラン候補
              </div>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {message.plans.map((plan) => (
                  <PlanCard
                    key={plan.plan_id}
                    plan={plan}
                    onSelect={() => onSelectPlan?.(plan)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Application Data */}
          {message.applicationData && (
            <div className="mt-4">
              <ApplicationDataCard data={message.applicationData} />
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div
          className={clsx(
            "text-xs text-dark-500 mt-2 px-2",
            isUser ? "text-right" : "text-left"
          )}
        >
          {formattedTime}
        </div>
      </div>
    </div>
  );
}
