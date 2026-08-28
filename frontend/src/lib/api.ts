/**
 * API client for the Lenny Growth Assistant backend.
 * All methods throw on HTTP errors with descriptive messages.
 */
import type {
  Artifact,
  HealthCheck,
  Message,
  Provider,
  Session,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.error || errorMessage;
    } catch {
      // Ignore JSON parse failure
    }
    throw new Error(errorMessage);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// ── Health ──────────────────────────────────────────────────────────────────

export const api = {
  health: {
    get: (): Promise<HealthCheck> => request('/health'),
  },

  // ── Sessions ────────────────────────────────────────────────────────────

  sessions: {
    list: (): Promise<{ sessions: Session[]; total: number }> =>
      request('/api/sessions'),

    create: (title?: string): Promise<Session> =>
      request('/api/sessions', {
        method: 'POST',
        body: JSON.stringify({ title: title || 'New Chat' }),
      }),

    get: (id: string): Promise<Session> =>
      request(`/api/sessions/${id}`),

    update: (id: string, title: string): Promise<Session> =>
      request(`/api/sessions/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title }),
      }),

    delete: (id: string): Promise<void> =>
      request(`/api/sessions/${id}`, { method: 'DELETE' }),
  },

  // ── Messages ─────────────────────────────────────────────────────────────

  messages: {
    list: (sessionId: string): Promise<{ messages: Message[]; total: number }> =>
      request(`/api/sessions/${sessionId}/messages`),

    create: (
      sessionId: string,
      content: string,
      provider?: Provider
    ): Promise<Message> =>
      request(`/api/sessions/${sessionId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content, provider }),
      }),
  },

  // ── Artifacts ─────────────────────────────────────────────────────────────

  artifacts: {
    get: (id: string): Promise<Artifact> =>
      request(`/api/artifacts/${id}`),

    listForSession: (sessionId: string): Promise<Artifact[]> =>
      request(`/api/artifacts/session/${sessionId}`),
  },
};
