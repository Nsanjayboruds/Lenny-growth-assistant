// API types matching backend Pydantic schemas

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SourceCitation {
  episode_title: string;
  guest: string;
  youtube_url: string | null;
  chunk_text: string;
  score: number;
}

export type MessageRole = 'user' | 'assistant';
export type Intent = 'CHAT' | 'SHIP30' | 'ARTIFACT';
export type Provider = 'ollama' | 'anthropic';
export type ArtifactType = 'markdown' | 'html';

export interface Message {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  sources: SourceCitation[] | null;
  intent: Intent | null;
  created_at: string;
}

export interface Artifact {
  id: string;
  session_id: string;
  artifact_type: ArtifactType;
  title: string;
  content: string;
  sanitized_content: string;
  created_at: string;
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: Record<string, unknown>;
  version: string;
}

// UI-only types
export interface ActiveArtifact {
  artifact: Artifact;
  isOpen: boolean;
}
