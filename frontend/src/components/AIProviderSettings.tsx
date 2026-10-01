import React, { useState, useEffect } from 'react';
import {
  AIProvider,
  AIModelOption,
  AIProviderManifestItem,
  ProviderValidationResult,
} from '../types/ai.ts';
import { apiClient } from '../services/api.ts';
import { useUserSettings } from '../hooks/useUserSettings.ts';
import {
  Cpu,
  Wand2,
  Sparkles,
  ChevronDown,
  Check,
  Loader2,
  RefreshCw,
  Sliders,
  ShieldCheck,
  AlertTriangle,
  Server,
  Zap,
  Lock,
} from 'lucide-react';

interface AIProviderSettingsProps {
  onInsertGeneratedText: (generatedText: string) => void;
  rawText: string;
  onError: (errorMsg: string) => void;
  disabled?: boolean;
}

const DEFAULT_PROVIDER_OPTIONS: { id: AIProvider; name: string; tag: string }[] = [
  { id: 'gemini', name: 'Google Gemini', tag: 'Fast 1M+ Context' },
  { id: 'groq', name: 'Groq', tag: 'Ultra-Low Latency' },
  { id: 'openrouter', name: 'OpenRouter', tag: 'Multi-Model Router' },
  { id: 'mistral', name: 'Mistral AI', tag: 'Codestral & NeMo' },
  { id: 'cohere', name: 'Cohere', tag: 'Command R+ Synthesis' },
  { id: 'huggingface', name: 'Hugging Face', tag: 'Open Weights' },
  { id: 'openai', name: 'OpenAI', tag: 'GPT-4o & o3-mini' },
  { id: 'custom', name: 'Custom Endpoint', tag: 'Ollama / Local / vLLM' },
];

const CURATED_MODELS: Record<AIProvider, AIModelOption[]> = {
  gemini: [
    {
      id: 'gemini-3.8-flash',
      name: 'Gemini 3.8 Flash',
      provider: 'gemini',
      contextWindow: '1M tokens',
      recommendedTask: 'Default. Superfast academic formatting & LaTeX normalization',
    },
    {
      id: 'gemini-3.1-pro-preview',
      name: 'Gemini 3.1 Pro',
      provider: 'gemini',
      contextWindow: '2M tokens',
      recommendedTask: 'Deep monograph synthesis & complex proofs',
    },
  ],
  groq: [
    {
      id: 'llama-3.3-70b-versatile',
      name: 'Llama 3.3 70B Versatile',
      provider: 'groq',
      contextWindow: '128K tokens',
      recommendedTask: 'High-speed academic reasoning & citation formatting',
    },
    {
      id: 'llama-3.1-8b-instant',
      name: 'Llama 3.1 8B Instant',
      provider: 'groq',
      contextWindow: '128K tokens',
      recommendedTask: 'Instant micro-edits & punctuation standardization',
    },
  ],
  openrouter: [
    {
      id: 'meta-llama/llama-3.3-70b-instruct',
      name: 'Meta Llama 3.3 70B',
      provider: 'openrouter',
      contextWindow: '131K tokens',
      recommendedTask: 'Balanced STEM & academic literature structuring',
    },
    {
      id: 'anthropic/claude-3.5-sonnet',
      name: 'Claude 3.5 Sonnet',
      provider: 'openrouter',
      contextWindow: '200K tokens',
      recommendedTask: 'Sophisticated prose & intricate academic tables',
    },
    {
      id: 'deepseek/deepseek-chat',
      name: 'DeepSeek V3',
      provider: 'openrouter',
      contextWindow: '64K tokens',
      recommendedTask: 'Mathematics & structured bibliography extraction',
    },
  ],
  mistral: [
    {
      id: 'mistral-small-latest',
      name: 'Mistral Small Latest',
      provider: 'mistral',
      contextWindow: '128K tokens',
      recommendedTask: 'Cost-efficient academic drafting',
    },
    {
      id: 'mistral-large-latest',
      name: 'Mistral Large Latest',
      provider: 'mistral',
      contextWindow: '128K tokens',
      recommendedTask: 'Multilingual monograph editing & deep literature review',
    },
    {
      id: 'codestral-latest',
      name: 'Codestral Latest',
      provider: 'mistral',
      contextWindow: '256K tokens',
      recommendedTask: 'LaTeX macros, algorithms, and pseudocode typesetting',
    },
  ],
  cohere: [
    {
      id: 'command-r-plus-08-2024',
      name: 'Command R+ (Aug 2024)',
      provider: 'cohere',
      contextWindow: '128K tokens',
      recommendedTask: 'Scholarly citations, RAG synthesis, and bibliography',
    },
    {
      id: 'command-r-08-2024',
      name: 'Command R (Aug 2024)',
      provider: 'cohere',
      contextWindow: '128K tokens',
      recommendedTask: 'Fast document restructuring',
    },
  ],
  huggingface: [
    {
      id: 'Qwen/Qwen2.5-72B-Instruct',
      name: 'Qwen 2.5 72B Instruct',
      provider: 'huggingface',
      contextWindow: '128K tokens',
      recommendedTask: 'High accuracy LaTeX and mathematical deduction',
    },
    {
      id: 'meta-llama/Llama-3.3-70B-Instruct',
      name: 'Llama 3.3 70B Instruct',
      provider: 'huggingface',
      contextWindow: '128K tokens',
      recommendedTask: 'Robust academic prose formatting',
    },
  ],
  openai: [
    {
      id: 'gpt-4o',
      name: 'GPT-4o',
      provider: 'openai',
      contextWindow: '128K tokens',
      recommendedTask: 'Versatile academic grammar and reference checks',
    },
    {
      id: 'gpt-4o-mini',
      name: 'GPT-4o Mini',
      provider: 'openai',
      contextWindow: '128K tokens',
      recommendedTask: 'Fast abstract and outline generation',
    },
    {
      id: 'o3-mini',
      name: 'o3-mini',
      provider: 'openai',
      contextWindow: '200K tokens',
      recommendedTask: 'Deep mathematical derivation & physics theorem proofs',
    },
  ],
  custom: [
    {
      id: 'custom-model',
      name: 'Local / Custom Model',
      provider: 'custom',
      contextWindow: '32K tokens',
      recommendedTask: 'Locally served model (Ollama / vLLM / LM Studio)',
    },
  ],
};

export const AIProviderSettings: React.FC<AIProviderSettingsProps> = ({
  onInsertGeneratedText,
  rawText,
  onError,
  disabled = false,
}) => {
  const {
    profile,
    selectProvider,
    selectModel,
    setApiKey,
    getApiKey,
    toggleProvider,
    isProviderEnabled,
    setCustomBaseUrl,
    updateAISettings,
  } = useUserSettings();

  const provider = profile?.ai?.selectedProvider || 'gemini';
  const selectedModel =
    profile?.ai?.selectedModel?.[provider] ||
    CURATED_MODELS[provider]?.[0]?.id ||
    'gemini-3.8-flash';
  const temperature = profile?.ai?.temperature ?? 0.2;
  const timeoutSec = profile?.ai?.timeoutSeconds ?? 30;
  const apiKey = getApiKey(provider);
  const customBaseUrl = profile?.ai?.customBaseUrls?.[provider] || 'http://localhost:11434/v1';
  const fallbackProvider = profile?.ai?.fallbackProvider || '';

  const [manifest, setManifest] = useState<AIProviderManifestItem[]>([]);
  const [dynamicModels, setDynamicModels] = useState<AIModelOption[]>([]);
  const [isDiscovering, setIsDiscovering] = useState<boolean>(false);

  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<ProviderValidationResult | null>(null);

  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [lastActionSuccess, setLastActionSuccess] = useState<string | null>(null);

  // Fetch provider manifest on mount
  useEffect(() => {
    let isMounted = true;
    apiClient
      .listProviders()
      .then((items) => {
        if (isMounted && items && items.length > 0) {
          setManifest(items);
        }
      })
      .catch((err) => {
        console.warn('Could not load AI providers manifest:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Update models list when provider changes
  useEffect(() => {
    const curated = CURATED_MODELS[provider] || [];
    setDynamicModels(curated);
    if (curated.length > 0 && !profile?.ai?.selectedModel?.[provider]) {
      selectModel(provider, curated[0].id);
    }
    setValidationResult(null);
  }, [provider]);

  const isCurrentProviderEnabled = isProviderEnabled(provider);

  const handleToggleProvider = () => {
    const nextState = !isCurrentProviderEnabled;
    toggleProvider(provider, nextState);
  };

  const handleDiscoverModels = async () => {
    setIsDiscovering(true);
    try {
      const discovered = await apiClient.discoverModels(provider);
      if (discovered && discovered.length > 0) {
        const formatted: AIModelOption[] = discovered.map((m: any) => ({
          id: m.id,
          name: m.name || m.id,
          provider,
          contextWindow: m.context_window ? `${Math.round(m.context_window / 1000)}K tokens` : 'Standard',
          recommendedTask: m.description || 'Discovered upstream model',
          isDiscovered: true,
        }));
        setDynamicModels(formatted);
        selectModel(provider, formatted[0].id);
        setLastActionSuccess(`Discovered ${formatted.length} models for ${provider}`);
      } else {
        setLastActionSuccess('Using curated models catalog.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Model discovery failed';
      onError(`Discovery failed: ${msg}`);
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleValidateConnection = async () => {
    setIsValidating(true);
    setValidationResult(null);
    try {
      const res = await apiClient.validateProvider(
        provider,
        apiKey.trim() || undefined,
        provider === 'custom' ? customBaseUrl.trim() : undefined
      );
      setValidationResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Validation failed';
      setValidationResult({
        provider_id: provider,
        is_valid: false,
        message: msg,
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleRunAiAssistant = async (actionType: 'abstract' | 'references' | 'math' | 'custom') => {
    if (disabled || isGenerating) return;

    if (!isCurrentProviderEnabled) {
      onError(`Provider '${provider}' is currently disabled in your local settings. Please enable it in provider settings.`);
      return;
    }

    let instruction = '';
    let promptContent = '';

    if (actionType === 'abstract') {
      if (!rawText.trim()) {
        onError('Please paste your academic document text first to generate an abstract.');
        return;
      }
      instruction =
        'You are an expert academic editor. Generate a concise, formal academic abstract (150-250 words) summarizing the background, methodology, results, and conclusion of the provided content.';
      promptContent = `Document text:\n\n${rawText.slice(0, 8000)}`;
    } else if (actionType === 'references') {
      if (!rawText.trim()) {
        onError('Please paste document content with citations to standardize references.');
        return;
      }
      instruction =
        'You are an academic citation specialist. Extract and format all bibliographic citations into standardized APA 7th edition references.';
      promptContent = `Document text:\n\n${rawText.slice(0, 8000)}`;
    } else if (actionType === 'math') {
      if (!rawText.trim()) {
        onError('Please paste text containing equations to normalize into standard LaTeX.');
        return;
      }
      instruction =
        'Normalize all mathematical formulas and expressions in the text into clean LaTeX delimiters ($...$ for inline, $$...$$ for display). Keep all other prose intact.';
      promptContent = `Document text:\n\n${rawText.slice(0, 8000)}`;
    } else {
      if (!customPrompt.trim()) {
        onError('Please enter an instruction or prompt for the AI assistant.');
        return;
      }
      instruction =
        'You are an expert academic editor and typesetter. Assist the author with scholarly formatting and drafting.';
      promptContent = `${customPrompt}\n\nContext document text:\n${rawText.slice(0, 8000)}`;
    }

    setIsGenerating(true);
    setLastActionSuccess(null);

    try {
      const response = await apiClient.generateAI({
        provider,
        model: selectedModel,
        prompt: promptContent,
        system_instruction: instruction,
        temperature,
        timeout: timeoutSec,
        api_key: apiKey.trim() || undefined,
        base_url: provider === 'custom' ? customBaseUrl.trim() : undefined,
        fallback_provider: fallbackProvider || undefined,
      });

      if (response && response.content) {
        onInsertGeneratedText(response.content);
        const fallbackNote = response.fallback_used
          ? ` (Fell back from ${response.original_provider || 'primary'} to ${response.provider})`
          : '';
        setLastActionSuccess(`Generated via ${response.provider} / ${response.model}${fallbackNote}`);
        if (actionType === 'custom') setCustomPrompt('');
      } else {
        onError('AI provider returned empty response.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'AI generation request failed';
      onError(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
      {/* Header & Toggle */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-white">Multi-Provider AI Architecture</h3>
          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-800/60">
            {DEFAULT_PROVIDER_OPTIONS.find((p) => p.id === provider)?.name || provider}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1.5 transition cursor-pointer"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>{isOpen ? 'Close Configuration' : 'Configure Providers'}</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Expanded Multi-Provider Configuration */}
      {isOpen && (
        <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-lg space-y-5 animate-in fade-in duration-150">
          {/* Provider Selection Badges */}
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">
              Select Provider Adapter
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {DEFAULT_PROVIDER_OPTIONS.map((item) => {
                const isSelected = provider === item.id;
                const provInfo = manifest.find((m) => m.id === item.id);
                const isAvailable = provInfo ? provInfo.is_available : false;
                const isEnabled = isProviderEnabled(item.id);

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectProvider(item.id)}
                    className={`text-left p-2.5 rounded-lg border transition-all cursor-pointer relative ${
                      isSelected
                        ? 'bg-indigo-950/70 border-indigo-500 ring-1 ring-indigo-500/50'
                        : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white truncate">{item.name}</span>
                      <div className="flex items-center gap-1">
                        {!isEnabled && (
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-500" title="Disabled in Local Settings" />
                        )}
                        {isEnabled && isAvailable && (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Configured" />
                        )}
                      </div>
                    </div>
                    <span className="text-[10px] text-slate-400 block mt-0.5 truncate">{item.tag}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Provider Status Bar & Enable/Disable Switch */}
          <div className="flex flex-wrap items-center justify-between p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-300 font-medium">Adapter Status (Local):</span>
              {isCurrentProviderEnabled ? (
                <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                  <Check className="w-3.5 h-3.5" /> Enabled
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-amber-400 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" /> Disabled in Your Profile
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-2 sm:mt-0">
              <button
                type="button"
                onClick={handleToggleProvider}
                className={`px-3 py-1 rounded text-xs font-medium border transition cursor-pointer ${
                  isCurrentProviderEnabled
                    ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                    : 'bg-emerald-950/60 border-emerald-800 text-emerald-300 hover:bg-emerald-900/60'
                }`}
              >
                {isCurrentProviderEnabled ? 'Disable in Profile' : 'Enable in Profile'}
              </button>
            </div>
          </div>

          {/* Model Selection & Custom Config */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Model Selector & Discovery */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="ai-model-select"
                  className="text-xs font-semibold text-slate-300 uppercase tracking-wider"
                >
                  Active Model
                </label>
                <button
                  type="button"
                  onClick={handleDiscoverModels}
                  disabled={isDiscovering || !isCurrentProviderEnabled}
                  className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition cursor-pointer disabled:opacity-50"
                  title="Query provider /models endpoint for latest supported models"
                >
                  <RefreshCw className={`w-3 h-3 ${isDiscovering ? 'animate-spin' : ''}`} />
                  <span>Discover Models</span>
                </button>
              </div>

              <select
                id="ai-model-select"
                value={selectedModel}
                onChange={(e) => selectModel(provider, e.target.value)}
                disabled={disabled || isGenerating || !isCurrentProviderEnabled}
                className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:border-indigo-500"
              >
                {dynamicModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.contextWindow}) {m.isDiscovered ? '★' : ''}
                  </option>
                ))}
              </select>
              <span className="text-[10px] text-slate-400 block mt-1">
                {dynamicModels.find((m) => m.id === selectedModel)?.recommendedTask ||
                  'Specialized formatting and reasoning model.'}
              </span>
            </div>

            {/* Custom Endpoint Base URL (for custom provider) or API Key override */}
            <div>
              {provider === 'custom' ? (
                <>
                  <label
                    htmlFor="custom-base-url"
                    className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5"
                  >
                    Custom Endpoint Base URL
                  </label>
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-slate-400 shrink-0" />
                    <input
                      id="custom-base-url"
                      type="text"
                      value={customBaseUrl}
                      onChange={(e) => setCustomBaseUrl(provider, e.target.value)}
                      placeholder="http://localhost:11434/v1"
                      className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>
                  <span className="text-[10px] text-slate-400 block mt-1">
                    Standard OpenAI-compatible URL (e.g. Ollama, LM Studio, vLLM). Stored locally.
                  </span>
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-1.5">
                    <label
                      htmlFor="api-key-override"
                      className="text-xs font-semibold text-slate-300 uppercase tracking-wider block"
                    >
                      Browser-Local API Key
                    </label>
                    <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                      <Lock className="w-3 h-3" />
                      Client-Local Only
                    </span>
                  </div>
                  <input
                    id="api-key-override"
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(provider, e.target.value)}
                    placeholder="Leave empty for server environment key, or paste personal key"
                    className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <span className="text-[10px] text-slate-400 block mt-1">
                    Saved in browser localStorage for this profile. Never stored on server database.
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Hyperparameters, Fallback & Connection Validation */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-800/80">
            {/* Temperature Slider */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Temperature
                </label>
                <span className="text-xs font-mono text-indigo-400">{temperature.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={(e) => updateAISettings({ temperature: parseFloat(e.target.value) })}
                disabled={disabled || isGenerating}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

            {/* Timeout Slider */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Timeout (Seconds)
                </label>
                <span className="text-xs font-mono text-indigo-400">{timeoutSec}s</span>
              </div>
              <input
                type="range"
                min="5"
                max="90"
                step="5"
                value={timeoutSec}
                onChange={(e) => updateAISettings({ timeoutSeconds: parseInt(e.target.value, 10) })}
                disabled={disabled || isGenerating}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

            {/* Explicit Fallback Selector */}
            <div>
              <label
                htmlFor="fallback-provider-select"
                className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1"
              >
                Explicit Fallback (Optional)
              </label>
              <select
                id="fallback-provider-select"
                value={fallbackProvider}
                onChange={(e) => updateAISettings({ fallbackProvider: e.target.value })}
                disabled={disabled || isGenerating}
                className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="">No Fallback (Fail Fast)</option>
                {DEFAULT_PROVIDER_OPTIONS.filter((p) => p.id !== provider).map((p) => (
                  <option key={p.id} value={p.id}>
                    Fallback: {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Validation Action and Outcome Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={handleValidateConnection}
              disabled={isValidating || !isProviderEnabled}
              className="px-3 py-1.5 rounded-lg bg-indigo-950/70 border border-indigo-700/80 hover:bg-indigo-900 text-xs font-medium text-indigo-200 flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
            >
              {isValidating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              )}
              <span>Test Adapter Connection</span>
            </button>

            {validationResult && (
              <div
                className={`text-xs px-3 py-1 rounded-md border flex items-center gap-1.5 ${
                  validationResult.is_valid
                    ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
                    : 'bg-rose-950/60 border-rose-800 text-rose-300'
                }`}
              >
                {validationResult.is_valid ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                )}
                <span>
                  {validationResult.message}
                  {validationResult.latency_ms ? ` (${validationResult.latency_ms}ms)` : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick Academic Enhancement Triggers */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
          Scholarly Assistant Actions
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => handleRunAiAssistant('abstract')}
            disabled={disabled || isGenerating || !isProviderEnabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 hover:bg-slate-800 hover:text-white transition disabled:opacity-50 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Generate Abstract</span>
          </button>

          <button
            type="button"
            onClick={() => handleRunAiAssistant('references')}
            disabled={disabled || isGenerating || !isProviderEnabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 hover:bg-slate-800 hover:text-white transition disabled:opacity-50 cursor-pointer"
          >
            <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
            <span>Standardize APA References</span>
          </button>

          <button
            type="button"
            onClick={() => handleRunAiAssistant('math')}
            disabled={disabled || isGenerating || !isProviderEnabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 hover:bg-slate-800 hover:text-white transition disabled:opacity-50 cursor-pointer"
          >
            <Zap className="w-3.5 h-3.5 text-indigo-400" />
            <span>Format Math Notation ($)</span>
          </button>

          {isGenerating && (
            <div className="flex items-center gap-1.5 text-xs text-indigo-400 animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Querying {DEFAULT_PROVIDER_OPTIONS.find((p) => p.id === provider)?.name}...</span>
            </div>
          )}

          {lastActionSuccess && (
            <div className="flex items-center gap-1 text-xs text-emerald-400">
              <Check className="w-3.5 h-3.5" />
              <span>{lastActionSuccess}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
