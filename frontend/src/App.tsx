import { useRef, useEffect, useCallback } from 'react';
import { useChat } from './hooks/useChat';
import { Header } from './components/Header';
import { ChatInput, ChatMessage } from './components/Chat';
import { WelcomeMessage } from './components/WelcomeMessage';
import { LoadingIndicator } from './components/LoadingIndicator';

function App() {
  const { messages, sessionId, isLoading, send, selectPlan, reset } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleExampleClick = useCallback((example: string) => {
    send(example);
  }, [send]);

  return (
    <div className="min-h-screen flex flex-col bg-dark-950">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-primary-950/50 via-dark-950 to-accent-950/30 pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary-900/20 via-transparent to-transparent pointer-events-none" />
      
      {/* Header */}
      <Header onReset={reset} sessionId={sessionId} />

      {/* Main content */}
      <main className="flex-1 flex flex-col relative max-w-6xl w-full mx-auto">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.length === 0 ? (
            <WelcomeMessage onExampleClick={handleExampleClick} />
          ) : (
            <>
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onSelectPlan={selectPlan}
                />
              ))}
              {isLoading && <LoadingIndicator />}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="sticky bottom-0 p-4 bg-gradient-to-t from-dark-950 via-dark-950/95 to-transparent pt-8">
          <div className="max-w-4xl mx-auto">
            <ChatInput
              onSend={send}
              disabled={isLoading}
              placeholder="出張の希望を入力してください（例：来週、大阪に2泊3日で出張したい）"
            />
            <p className="text-center text-xs text-dark-600 mt-3">
              AIの回答は参考情報です。実際の予約・申請は別途ご確認ください。
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;



