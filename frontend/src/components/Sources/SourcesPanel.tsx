import React from 'react';
import type { SourceCitation } from '../../types';
import { ExternalLink, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import clsx from 'clsx';

interface SourcesPanelProps {
  sources: SourceCitation[];
}

function truncateText(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars) + '…';
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? 'text-green-400 bg-green-400/10' :
    pct >= 65 ? 'text-brand-400 bg-brand-400/10' :
    'text-slate-400 bg-slate-400/10';

  return (
    <span className={clsx('text-xs px-1.5 py-0.5 rounded font-mono', color)}>
      {pct}%
    </span>
  );
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [expandedSource, setExpandedSource] = React.useState<number | null>(null);

  if (!sources || sources.length === 0) return null;

  const visibleSources = isExpanded ? sources : sources.slice(0, 2);

  return (
    <div className="mt-3 animate-fade-in">
      <button
        onClick={() => setIsExpanded((v) => !v)}
        className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-slate-200 mb-2 transition-colors"
        aria-expanded={isExpanded}
        aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${sources.length} source${sources.length !== 1 ? 's' : ''}`}
      >
        <BookOpen size={12} />
        <span>
          {sources.length} Source{sources.length !== 1 ? 's' : ''}
        </span>
        {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      <div className="space-y-2">
        {visibleSources.map((source, i) => (
          <div
            key={i}
            className="bg-surface-700 border border-surface-500 rounded-lg overflow-hidden"
          >
            {/* Source header */}
            <div className="flex items-start justify-between gap-2 px-3 py-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-brand-300 truncate">
                    {source.episode_title}
                  </span>
                  <ScoreBadge score={source.score} />
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Guest: {source.guest}
                </p>
              </div>

              <div className="flex items-center gap-1 flex-shrink-0">
                {source.youtube_url && (
                  <a
                    href={source.youtube_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`Open episode: ${source.episode_title} on YouTube`}
                    className="p-1 rounded text-slate-500 hover:text-brand-400 transition-colors"
                  >
                    <ExternalLink size={12} />
                  </a>
                )}
                <button
                  onClick={() =>
                    setExpandedSource(expandedSource === i ? null : i)
                  }
                  aria-label={expandedSource === i ? 'Hide excerpt' : 'Show excerpt'}
                  className="p-1 rounded text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {expandedSource === i ? (
                    <ChevronUp size={12} />
                  ) : (
                    <ChevronDown size={12} />
                  )}
                </button>
              </div>
            </div>

            {/* Expandable excerpt */}
            {expandedSource === i && (
              <div className="px-3 pb-2 border-t border-surface-600">
                <p className="text-xs text-slate-400 leading-relaxed mt-2 italic">
                  "{truncateText(source.chunk_text, 400)}"
                </p>
              </div>
            )}
          </div>
        ))}

        {!isExpanded && sources.length > 2 && (
          <button
            onClick={() => setIsExpanded(true)}
            className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
          >
            + {sources.length - 2} more source{sources.length - 2 !== 1 ? 's' : ''}
          </button>
        )}
      </div>
    </div>
  );
}
