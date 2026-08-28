import type { Provider } from '../../types';
import { PROVIDERS } from '../../hooks/useProvider';
import { Zap, Cloud } from 'lucide-react';
import clsx from 'clsx';

interface ModelSelectorProps {
  selectedProvider: Provider;
  onProviderChange: (provider: Provider) => void;
  anthropicAvailable?: boolean;
}

export function ModelSelector({
  selectedProvider,
  onProviderChange,
  anthropicAvailable = false,
}: ModelSelectorProps) {
  return (
    <div className="p-3 border-t border-surface-600">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
        Model
      </p>
      <div className="space-y-1">
        {PROVIDERS.map((p) => {
          const isSelected = selectedProvider === p.id;
          const isDisabled = p.id === 'anthropic' && !anthropicAvailable;

          return (
            <button
              key={p.id}
              id={`model-selector-${p.id}`}
              onClick={() => !isDisabled && onProviderChange(p.id)}
              disabled={isDisabled}
              aria-pressed={isSelected}
              aria-label={`Use ${p.label} model${isDisabled ? ' (unavailable — API key not configured)' : ''}`}
              title={isDisabled ? 'Anthropic API key not configured in .env' : undefined}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-150',
                isSelected
                  ? 'bg-brand-600/30 border border-brand-500/50 text-brand-300'
                  : isDisabled
                  ? 'opacity-40 cursor-not-allowed text-slate-500'
                  : 'hover:bg-surface-600 text-slate-400 hover:text-slate-200 border border-transparent'
              )}
            >
              <span className="text-base leading-none">
                {p.id === 'ollama' ? (
                  <Zap size={14} className={isSelected ? 'text-brand-400' : 'text-slate-500'} />
                ) : (
                  <Cloud size={14} className={isSelected ? 'text-brand-400' : 'text-slate-500'} />
                )}
              </span>
              <span className="flex-1 text-left">
                <span className="block font-medium">{p.label}</span>
                <span className="block text-xs text-slate-500">{p.sublabel}</span>
              </span>
              {isSelected && (
                <span
                  className="w-2 h-2 rounded-full bg-brand-400 flex-shrink-0"
                  aria-hidden="true"
                />
              )}
              {isDisabled && (
                <span className="text-xs text-slate-600 flex-shrink-0">No key</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
