export type AIProvider =
  | 'gemini'
  | 'groq'
  | 'openrouter'
  | 'mistral'
  | 'cohere'
  | 'huggingface'
  | 'openai'
  | 'custom';

export interface AIGenerateRequest {
  prompt: string;
  system_instruction?: string;
  provider?: AIProvider;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  timeout?: number;
  api_key?: string;
  base_url?: string;
  fallback_provider?: string;
  fallback_model?: string;
  retries?: number;
}

export interface AIGenerateResponse {
  success: boolean;
  content: string;
  model: string;
  provider: AIProvider;
  fallback_used?: boolean;
  original_provider?: string;
  usage?: {
    prompt_tokens?: number;
    candidates_tokens?: number;
    total_tokens?: number;
  };
}

export interface AIErrorDetail {
  code: string;
  message: string;
  provider?: string;
}

export interface AIErrorResponse {
  success: boolean;
  error: AIErrorDetail;
}

export interface AIModelOption {
  id: string;
  name: string;
  provider: AIProvider;
  contextWindow: string;
  recommendedTask: string;
  description?: string;
  isDiscovered?: boolean;
}

export interface AIProviderManifestItem {
  id: AIProvider;
  name: string;
  is_available: boolean;
  is_enabled: boolean;
  default_model: string;
  supported_models: {
    id: string;
    name: string;
    context_window?: number;
    supports_formatting: boolean;
    description?: string;
    is_discovered?: boolean;
  }[];
  supports_model_discovery: boolean;
  requires_base_url: boolean;
  base_url?: string;
}

export interface ProviderValidationResult {
  provider_id: string;
  is_valid: boolean;
  message: string;
  latency_ms?: number;
  discovered_models_count?: number;
}
