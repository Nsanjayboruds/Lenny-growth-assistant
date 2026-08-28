import React from 'react';
import type { Session } from '../../types';
import { Plus, MessageSquare, Trash2, Mic } from 'lucide-react';
import clsx from 'clsx';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  isLoading?: boolean;
  children?: React.ReactNode; // model selector slot
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function Sidebar({
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
  onDeleteSession,
  isLoading,
  children,
}: SidebarProps) {
  const [hoveredId, setHoveredId] = React.useState<string | null>(null);

  const groupedSessions = React.useMemo(() => {
    const groups: Record<string, Session[]> = {};
    sessions.forEach((s) => {
      const label = formatDate(s.updated_at);
      if (!groups[label]) groups[label] = [];
      groups[label].push(s);
    });
    return groups;
  }, [sessions]);

  return (
    <aside
      className="flex flex-col h-full w-64 bg-surface-800 border-r border-surface-600"
      aria-label="Sidebar navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-surface-600">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center flex-shrink-0 glow-brand">
          <Mic size={16} className="text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-white leading-tight">Lenny</h1>
          <p className="text-xs text-slate-500">Growth Assistant</p>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-3 border-b border-surface-600">
        <button
          id="new-chat-button"
          onClick={onNewSession}
          disabled={isLoading}
          aria-label="Start a new chat session"
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2.5 rounded-lg',
            'bg-brand-600 hover:bg-brand-500 text-white font-medium text-sm',
            'transition-all duration-150 active:scale-95',
            'focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2 focus:ring-offset-surface-800',
            isLoading && 'opacity-60 cursor-not-allowed'
          )}
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Session History */}
      <nav
        className="flex-1 overflow-y-auto py-2"
        aria-label="Chat history"
      >
        {sessions.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <MessageSquare size={32} className="text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No conversations yet</p>
            <p className="text-xs text-slate-600 mt-1">Start a new chat above</p>
          </div>
        ) : (
          Object.entries(groupedSessions).map(([group, groupSessions]) => (
            <div key={group} className="mb-2">
              <p className="px-4 py-1 text-xs font-medium text-slate-500 uppercase tracking-wider">
                {group}
              </p>
              {groupSessions.map((session) => (
                <div
                  key={session.id}
                  className="relative group"
                  onMouseEnter={() => setHoveredId(session.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <button
                    onClick={() => onSelectSession(session.id)}
                    aria-current={activeSessionId === session.id ? 'page' : undefined}
                    aria-label={`Open chat: ${session.title}`}
                    className={clsx(
                      'w-full text-left px-4 py-2.5 text-sm transition-colors duration-100',
                      'focus:outline-none focus:ring-inset focus:ring-2 focus:ring-brand-500',
                      activeSessionId === session.id
                        ? 'bg-brand-600/20 text-white border-r-2 border-brand-500'
                        : 'text-slate-400 hover:bg-surface-700 hover:text-slate-200'
                    )}
                  >
                    <span className="block truncate pr-8">{session.title}</span>
                    <span className="block text-xs text-slate-600 mt-0.5">
                      {session.message_count} msg{session.message_count !== 1 ? 's' : ''}
                    </span>
                  </button>

                  {/* Delete button — visible on hover */}
                  {hoveredId === session.id && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                      aria-label={`Delete chat: ${session.title}`}
                      className={clsx(
                        'absolute right-2 top-1/2 -translate-y-1/2',
                        'p-1.5 rounded-md text-slate-600 hover:text-red-400 hover:bg-surface-600',
                        'transition-colors duration-100',
                        'focus:outline-none focus:ring-2 focus:ring-red-400'
                      )}
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          ))
        )}
      </nav>

      {/* Model Selector (injected as children) */}
      {children}
    </aside>
  );
}
