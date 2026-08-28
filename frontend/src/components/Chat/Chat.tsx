import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, Provider } from '../../types';
import { SourcesPanel } from '../Sources/SourcesPanel';
import { Send, Bot, User, AlertCircle, FileText, PenLine } from 'lucide-react';
import clsx from 'clsx';

interface ChatProps {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  selectedProvider: Provider;
  sessionTitle?: string;
  onSendMessage: (content: string) => void;
  onViewArtifact?: () => void;
  hasArtifact?: boolean;
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1" aria-label="Assistant is typing">
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-brand-400" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-brand-400" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-brand-400" />
    </div>
  );
}

function IntentBadge({ intent }: { intent: string | null }) {
  if (!intent || intent === 'CHAT') return null;
  const config = {
    SHIP30: { label: 'Essay', icon: <PenLine size={10} />, className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
    ARTIFACT: { label: 'Artifact', icon: <FileText size={10} />, className: 'bg-amber-500/10 text-amber-400 border-amber-500/30' },
  }[intent];

  if (!config) return null;

  return (
    <span className={clsx('inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border font-medium', config.className)}>
      {config.icon}
      {config.label}
    </span>
  );
}

function MessageBubble({ message, onViewArtifact }: { message: Message; onViewArtifact?: () => void }) {
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx(
        'flex gap-3 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
          isUser
            ? 'bg-brand-600'
            : 'bg-surface-600 border border-surface-500'
        )}
        aria-hidden="true"
      >
        {isUser ? (
          <User size={14} className="text-white" />
        ) : (
          <Bot size={14} className="text-brand-400" />
        )}
      </div>

      {/* Bubble */}
      <div className={clsx('flex-1 min-w-0', isUser && 'flex flex-col items-end')}>
        <div
          className={clsx(
            'rounded-2xl px-4 py-3 max-w-2xl',
            isUser
              ? 'bg-brand-600 text-white rounded-tr-sm'
              : 'bg-surface-700 border border-surface-500 rounded-tl-sm'
          )}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <div className="prose-chat text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Badges + sources (assistant only) */}
        {!isUser && (
          <div className="mt-1 pl-0 max-w-2xl w-full">
            <div className="flex items-center gap-2 mb-1">
              <IntentBadge intent={message.intent} />
              {message.intent === 'ARTIFACT' && onViewArtifact && (
                <button
                  onClick={onViewArtifact}
                  className="text-xs text-amber-400 hover:text-amber-300 underline"
                  aria-label="Open artifact viewer"
                >
                  View Artifact →
                </button>
              )}
            </div>
            {message.sources && message.sources.length > 0 && (
              <SourcesPanel sources={message.sources} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  "What does Lenny say about finding product-market fit?",
  "How do the best PMs approach prioritization?",
  "Write a Ship 30 essay about growth loops",
  "What are the key metrics for a consumer startup?",
];

export function Chat({
  messages,
  isLoading,
  error,
  selectedProvider,
  sessionTitle,
  onSendMessage,
  onViewArtifact,
  hasArtifact,
}: ChatProps) {
  const [input, setInput] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setInput('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize textarea
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-600 bg-surface-800/50 backdrop-blur-sm">
        <div>
          <h2 className="font-semibold text-white text-sm">
            {sessionTitle || 'New Chat'}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {selectedProvider === 'ollama' ? '⚡ Ollama — Local' : '☁️ Claude — Cloud'}
          </p>
        </div>
        {hasArtifact && (
          <button
            onClick={onViewArtifact}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition-colors"
            aria-label="Open artifact viewer"
          >
            <FileText size={12} />
            View Artifact
          </button>
        )}
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto px-6 py-6 space-y-6"
        role="log"
        aria-live="polite"
        aria-label="Chat conversation"
      >
        {isEmpty ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 flex items-center justify-center mb-4 glow-brand-strong">
              <Bot size={28} className="text-white" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Ask Lenny Anything
            </h3>
            <p className="text-sm text-slate-400 mb-6 max-w-sm">
              Grounded in 269 Lenny's Podcast transcripts. Ask product management, growth, and strategy questions.
            </p>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    textareaRef.current?.focus();
                  }}
                  className="text-left text-sm px-4 py-2.5 rounded-xl bg-surface-700 border border-surface-500 text-slate-300 hover:border-brand-500/50 hover:bg-surface-600 transition-all duration-150"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onViewArtifact={msg.intent === 'ARTIFACT' ? onViewArtifact : undefined}
              />
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div className="flex gap-3 animate-fade-in">
                <div className="w-8 h-8 rounded-lg bg-surface-600 border border-surface-500 flex items-center justify-center flex-shrink-0">
                  <Bot size={14} className="text-brand-400" />
                </div>
                <div className="bg-surface-700 border border-surface-500 rounded-2xl rounded-tl-sm px-4 py-3">
                  <TypingIndicator />
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div
                className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 animate-fade-in"
                role="alert"
              >
                <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-300">Error</p>
                  <p className="text-sm text-red-400/80 mt-0.5">{error}</p>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} aria-hidden="true" />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-surface-600 bg-surface-800/50 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-end gap-3 bg-surface-700 border border-surface-500 rounded-2xl px-4 py-3 focus-within:border-brand-500/70 transition-colors">
            <textarea
              ref={textareaRef}
              id="chat-input"
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask a product or growth question... (Shift+Enter for new line)"
              rows={1}
              disabled={isLoading}
              aria-label="Chat message input"
              className={clsx(
                'flex-1 bg-transparent text-sm text-white placeholder-slate-500',
                'resize-none outline-none min-h-[1.5rem] max-h-[200px]',
                'disabled:opacity-60'
              )}
              style={{ height: 'auto' }}
            />
            <button
              type="submit"
              id="send-button"
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
              className={clsx(
                'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center',
                'transition-all duration-150 active:scale-95',
                input.trim() && !isLoading
                  ? 'bg-brand-600 hover:bg-brand-500 text-white'
                  : 'bg-surface-600 text-slate-600 cursor-not-allowed'
              )}
            >
              <Send size={14} />
            </button>
          </div>
          <p className="text-xs text-slate-600 mt-1.5 text-center">
            Grounded in Lenny's Podcast transcripts · Not affiliated with Lenny Rachitsky
          </p>
        </form>
      </div>
    </div>
  );
}
