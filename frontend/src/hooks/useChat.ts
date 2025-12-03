import { useState, useCallback } from 'react';
import { sendMessage, confirmPlan } from '../api';
import type { ChatMessage, TravelPlan, ApplicationPayload } from '../types';

const USER_ID = 'demo-user-1';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: generateId(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  }, []);

  const send = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    setError(null);
    
    // Add user message
    addMessage({
      role: 'user',
      type: 'text',
      content: content.trim(),
    });

    setIsLoading(true);

    try {
      const response = await sendMessage({
        session_id: sessionId,
        message: content.trim(),
        user_id: USER_ID,
      });

      setSessionId(response.session_id);

      // Add assistant message
      for (const msg of response.messages) {
        addMessage({
          role: msg.role,
          type: msg.type,
          content: msg.content,
          plans: response.plans.length > 0 ? response.plans : undefined,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(message);
      addMessage({
        role: 'assistant',
        type: 'text',
        content: `申し訳ありません。エラーが発生しました: ${message}`,
      });
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, addMessage]);

  const selectPlan = useCallback(async (plan: TravelPlan): Promise<ApplicationPayload | null> => {
    if (!sessionId) {
      setError('セッションが見つかりません');
      return null;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await confirmPlan({
        plan_id: plan.plan_id,
        session_id: sessionId,
        user_id: USER_ID,
      });

      if (response.status === 'confirmed' && response.application_payload) {
        addMessage({
          role: 'assistant',
          type: 'application_data',
          content: `「${plan.label}」で申請データを作成しました。`,
          applicationData: response.application_payload,
        });
        return response.application_payload;
      } else {
        throw new Error(response.error_message || 'プラン確定に失敗しました');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(message);
      addMessage({
        role: 'assistant',
        type: 'text',
        content: `申し訳ありません。プラン確定中にエラーが発生しました: ${message}`,
      });
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addMessage]);

  const reset = useCallback(() => {
    setMessages([]);
    setSessionId(undefined);
    setError(null);
  }, []);

  return {
    messages,
    sessionId,
    isLoading,
    error,
    send,
    selectPlan,
    reset,
  };
}

