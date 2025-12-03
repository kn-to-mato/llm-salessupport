import type {
  ChatRequest,
  ChatResponse,
  PlanConfirmRequest,
  PlanConfirmResponse,
} from '../types';

const API_BASE = '/api';

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to send message');
  }

  return response.json();
}

export async function confirmPlan(request: PlanConfirmRequest): Promise<PlanConfirmResponse> {
  const response = await fetch(`${API_BASE}/plan/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to confirm plan');
  }

  return response.json();
}

