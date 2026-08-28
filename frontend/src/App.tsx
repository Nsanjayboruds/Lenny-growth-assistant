import { useState, useEffect } from 'react';
import type { Session, Message, Artifact } from './types';
import { api } from './lib/api';
import { Sidebar } from './components/Sidebar/Sidebar';
import { Chat } from './components/Chat/Chat';
import { ArtifactViewer } from './components/ArtifactViewer/ArtifactViewer';
import { ModelSelector } from './components/ModelSelector/ModelSelector';
import { useProvider } from './hooks/useProvider';

function App() {
  // State
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [isArtifactOpen, setIsArtifactOpen] = useState(false);
  const [anthropicAvailable, setAnthropicAvailable] = useState(false);

  const { provider, setProvider } = useProvider();

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
    checkHealth();
  }, []);

  // Load messages when active session changes
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  const checkHealth = async () => {
    try {
      const health = await api.health.get();
      // Check if Anthropic is configured (we check this from health data)
      // If LLM provider check returns "ok" for anthropic, it's available
      const llmCheck = health.checks?.llm_provider as Record<string, unknown>;
      if (llmCheck?.provider?.toString().toLowerCase().includes('anthropic')) {
        setAnthropicAvailable(llmCheck.status === 'ok');
      }
    } catch {
      // health check failure doesn't break the app
    }
  };

  const loadSessions = async () => {
    try {
      const data = await api.sessions.list();
      setSessions(data.sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  };

  const loadMessages = async (sessionId: string) => {
    setIsLoadingMessages(true);
    setSendError(null);
    try {
      const data = await api.messages.list(sessionId);
      setMessages(data.messages);

      // Check for artifacts in messages
      const artifactMessages = data.messages.filter((m) => m.intent === 'ARTIFACT');
      if (artifactMessages.length > 0) {
        // Load the most recent artifact for this session
        try {
          const artifacts = await api.artifacts.listForSession(sessionId);
          if (artifacts.length > 0) {
            setActiveArtifact(artifacts[0]);
          }
        } catch {
          // ignore artifact load failure
        }
      }
    } catch (err) {
      console.error('Failed to load messages:', err);
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const handleNewSession = async () => {
    try {
      const session = await api.sessions.create();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setActiveArtifact(null);
      setIsArtifactOpen(false);
      setSendError(null);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleSelectSession = (id: string) => {
    if (id === activeSessionId) return;
    setActiveSessionId(id);
    setActiveArtifact(null);
    setIsArtifactOpen(false);
    setSendError(null);
  };

  const handleDeleteSession = async (id: string) => {
    if (!confirm('Delete this conversation?')) return;
    try {
      await api.sessions.delete(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
        setActiveArtifact(null);
        setIsArtifactOpen(false);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!activeSessionId) {
      // Auto-create a session if none is active
      try {
        const session = await api.sessions.create();
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(session.id);
        // Small delay to let session state settle, then send
        await new Promise((r) => setTimeout(r, 100));
        await sendMessage(session.id, content);
        return;
      } catch {
        setSendError('Failed to create session. Please try again.');
        return;
      }
    }
    await sendMessage(activeSessionId, content);
  };

  const sendMessage = async (sessionId: string, content: string) => {
    // Optimistically add user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      sources: null,
      intent: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsSending(true);
    setSendError(null);

    try {
      const assistantMsg = await api.messages.create(sessionId, content, provider);
      
      // Replace temp message with real user message by reloading
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...filtered, assistantMsg];
      });

      // Reload messages to get the persisted user message with correct ID
      const data = await api.messages.list(sessionId);
      setMessages(data.messages);

      // Update session title in sidebar
      setSessions((prev) =>
        prev.map((s) => s.id === sessionId ? { ...s, message_count: s.message_count + 2 } : s)
      );

      // If an artifact was generated, load it
      if (assistantMsg.intent === 'ARTIFACT') {
        try {
          const artifacts = await api.artifacts.listForSession(sessionId);
          if (artifacts.length > 0) {
            setActiveArtifact(artifacts[0]);
            setIsArtifactOpen(true);
          }
        } catch {
          // ignore
        }
      }
    } catch (err) {
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
      setSendError(err instanceof Error ? err.message : 'Failed to send message. Please try again.');
    } finally {
      setIsSending(false);
      // Refresh sessions to get updated title
      loadSessions();
    }
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const showArtifact = isArtifactOpen && activeArtifact;

  return (
    <div className="flex h-screen bg-surface-900 text-white overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      >
        <ModelSelector
          selectedProvider={provider}
          onProviderChange={setProvider}
          anthropicAvailable={anthropicAvailable}
        />
      </Sidebar>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat Area */}
        <div className={`flex flex-col ${showArtifact ? 'w-1/2' : 'flex-1'} transition-all duration-300`}>
          {activeSessionId || messages.length > 0 ? (
            <Chat
              messages={messages}
              isLoading={isSending || isLoadingMessages}
              error={sendError}
              selectedProvider={provider}
              sessionTitle={activeSession?.title}
              onSendMessage={handleSendMessage}
              onViewArtifact={() => setIsArtifactOpen(true)}
              hasArtifact={!!activeArtifact}
            />
          ) : (
            /* No session selected — show welcome screen */
            <div className="flex flex-col items-center justify-center h-full text-center px-8 animate-fade-in">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500 to-brand-800 flex items-center justify-center mb-6 glow-brand-strong">
                <span className="text-3xl">🎙️</span>
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">
                Lenny Growth Assistant
              </h2>
              <p className="text-slate-400 max-w-md mb-6 leading-relaxed">
                Ask product management and growth questions, grounded in{' '}
                <span className="text-brand-400">269 Lenny's Podcast transcripts</span>.
                Get answers with source citations from real episodes.
              </p>
              <div className="flex flex-col gap-3 w-full max-w-xs">
                <button
                  onClick={handleNewSession}
                  id="welcome-new-chat-button"
                  className="px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white font-semibold rounded-xl transition-all duration-150 active:scale-95 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2 focus:ring-offset-surface-900"
                >
                  Start a New Chat
                </button>
              </div>
              <div className="mt-8 grid grid-cols-3 gap-3 text-center max-w-sm">
                {[
                  { icon: '📚', label: '269 Episodes' },
                  { icon: '🎯', label: 'RAG Grounded' },
                  { icon: '⚡', label: 'Local Ollama' },
                ].map((f) => (
                  <div key={f.label} className="bg-surface-800 border border-surface-600 rounded-xl p-3">
                    <div className="text-xl mb-1">{f.icon}</div>
                    <div className="text-xs text-slate-400">{f.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Artifact Viewer Panel */}
        {showArtifact && activeArtifact && (
          <div className="w-1/2 border-l border-surface-600 overflow-hidden">
            <ArtifactViewer
              artifact={activeArtifact}
              onClose={() => setIsArtifactOpen(false)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
