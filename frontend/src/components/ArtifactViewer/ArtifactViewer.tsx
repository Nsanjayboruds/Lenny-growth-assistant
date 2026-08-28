import React, { useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Artifact } from '../../types';
import { X, Code, Eye, ExternalLink, Copy, Check } from 'lucide-react';
import clsx from 'clsx';

interface ArtifactViewerProps {
  artifact: Artifact;
  onClose: () => void;
}

type ViewMode = 'preview' | 'source';

/**
 * ArtifactViewer renders generated artifacts.
 *
 * Security model:
 *   - HTML artifacts: rendered in a sandboxed iframe with sandbox="allow-same-origin"
 *     — Scripts are blocked (no allow-scripts)
 *     — Form submission is blocked (no allow-forms)
 *     — Top-level navigation is blocked (no allow-top-navigation)
 *     — The HTML is also pre-sanitized server-side using bleach
 *   - Markdown artifacts: rendered via react-markdown (safe by default)
 */
export function ArtifactViewer({ artifact, onClose }: ArtifactViewerProps) {
  const [viewMode, setViewMode] = React.useState<ViewMode>('preview');
  const [copied, setCopied] = React.useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const isHtml = artifact.artifact_type === 'html';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard may not be available
    }
  };

  const handleOpenExternal = () => {
    const blob = new Blob([artifact.sanitized_content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  };

  return (
    <div className="flex flex-col h-full bg-surface-800 border-l border-surface-600 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-600 bg-surface-750">
        <div className="flex-1 min-w-0 mr-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-0.5">
            Artifact · {artifact.artifact_type.toUpperCase()}
          </p>
          <h3 className="text-sm font-semibold text-white truncate">
            {artifact.title}
          </h3>
        </div>

        <div className="flex items-center gap-1">
          {/* View mode toggle (HTML only) */}
          {isHtml && (
            <div className="flex bg-surface-700 rounded-lg p-0.5 mr-1">
              <button
                onClick={() => setViewMode('preview')}
                className={clsx(
                  'flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors',
                  viewMode === 'preview'
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                )}
                aria-pressed={viewMode === 'preview'}
                aria-label="Preview artifact"
              >
                <Eye size={11} />
                Preview
              </button>
              <button
                onClick={() => setViewMode('source')}
                className={clsx(
                  'flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors',
                  viewMode === 'source'
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                )}
                aria-pressed={viewMode === 'source'}
                aria-label="View source code"
              >
                <Code size={11} />
                Source
              </button>
            </div>
          )}

          {/* Copy */}
          <button
            onClick={handleCopy}
            title="Copy to clipboard"
            aria-label="Copy artifact content to clipboard"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-600 transition-colors"
          >
            {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
          </button>

          {/* Open in new tab (HTML) */}
          {isHtml && viewMode === 'preview' && (
            <button
              onClick={handleOpenExternal}
              title="Open in new tab"
              aria-label="Open artifact in new browser tab"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-600 transition-colors"
            >
              <ExternalLink size={14} />
            </button>
          )}

          {/* Close */}
          <button
            onClick={onClose}
            aria-label="Close artifact viewer"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-600 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {isHtml && viewMode === 'preview' ? (
          /**
           * SANDBOXED IFRAME
           * sandbox="allow-same-origin" allows:
           *   - CSS from same origin (needed for styles)
           * sandbox BLOCKS:
           *   - JavaScript execution (no allow-scripts)
           *   - Form submission (no allow-forms)
           *   - Top-level navigation (no allow-top-navigation)
           *   - Popups (no allow-popups)
           *   - Pointer lock, downloads, and other privilege escalations
           */
          <iframe
            ref={iframeRef}
            title={`Artifact: ${artifact.title}`}
            sandbox="allow-same-origin"
            srcDoc={artifact.sanitized_content}
            className="w-full h-full bg-white"
            aria-label={`Rendered artifact: ${artifact.title}`}
          />
        ) : (
          <div className="h-full overflow-y-auto">
            {isHtml && viewMode === 'source' ? (
              // Source view for HTML
              <div className="p-4">
                <pre className="text-xs font-mono text-slate-300 bg-surface-900 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
                  <code>{artifact.content}</code>
                </pre>
              </div>
            ) : (
              // Markdown rendered view
              <div className="p-6 prose-chat">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {artifact.content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Security notice for HTML */}
      {isHtml && viewMode === 'preview' && (
        <div className="px-4 py-2 border-t border-surface-600 bg-surface-900/50">
          <p className="text-xs text-slate-600 flex items-center gap-1">
            <span>🔒</span>
            Sandboxed iframe — scripts and navigation disabled
          </p>
        </div>
      )}
    </div>
  );
}
