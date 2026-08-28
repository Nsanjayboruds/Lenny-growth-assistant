import { useState } from 'react';
import type { Provider } from '../types';
export type ProviderOption = {
  id: Provider;
  label: string;
  sublabel: string;
  icon: string;
};

export const PROVIDERS: ProviderOption[] = [
  {
    id: 'ollama',
    label: 'Ollama',
    sublabel: 'Local • llama3.2',
    icon: '⚡',
  },
  {
    id: 'anthropic',
    label: 'Claude',
    sublabel: 'Cloud • claude-3-5-haiku',
    icon: '☁️',
  },
];

export function useProvider() {
  const [provider, setProvider] = useState<Provider>('ollama');
  return { provider, setProvider };
}
