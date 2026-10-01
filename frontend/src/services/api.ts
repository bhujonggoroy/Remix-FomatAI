/**
 * FormatAI Dedicated API Client.
 *
 * All HTTP communication with the Python FastAPI backend is centralized here.
 * The backend URL is retrieved from the VITE_API_BASE_URL environment variable,
 * falling back to the current origin relative proxy path ('') to ensure resilience
 * across dev servers, preview iframes, and containerized deployments.
 */

import {
  DocumentAnalysis,
  DocumentProcessRequest,
  DocumentProcessResponse,
  DocumentExportRequest,
} from '../types/document.ts';
import {
  AIGenerateRequest,
  AIGenerateResponse,
  AIProviderManifestItem,
  ProviderValidationResult,
} from '../types/ai.ts';
import {
  DEFAULT_SKILL_MANIFEST,
  SkillInfo,
  SkillValidationResult,
  SkillExecutionResult,
} from '../types/skills.ts';

export interface HealthCheckResponse {
  status: 'ok' | 'starting' | 'error';
  service: string;
  backend: string;
  version?: string;
  environment?: string;
  uptime_seconds?: number;
  message?: string;
}

export class ApiError extends Error {
  statusCode: number;
  errorCode: string;
  details?: unknown;

  constructor(message: string, statusCode: number, errorCode = 'API_ERROR', details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.details = details;
  }
}

/**
 * Returns the resolved backend API base URL without trailing slash.
 */
export function getBackendBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  // Safe default: relative path to the host server proxy
  return '';
}

/**
 * Common request helper with robust JSON and binary error extraction.
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getBackendBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const defaultHeaders: Record<string, string> = {
    Accept: 'application/json',
  };

  if (options.body && typeof options.body === 'string') {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const mergedHeaders = {
    ...defaultHeaders,
    ...(options.headers as Record<string, string>),
  };

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: mergedHeaders,
    });
  } catch (networkErr: unknown) {
    const msg = networkErr instanceof Error ? networkErr.message : 'Network request failed';
    throw new ApiError(
      `Cannot connect to FastAPI backend at ${url || '/'}: ${msg}. Please ensure the Python service is running.`,
      0,
      'NETWORK_DISCONNECTED'
    );
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let errorCode = 'HTTP_ERROR';
    let details: unknown = null;

    try {
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const errorBody = await response.json();
        details = errorBody;
        if (errorBody.detail) {
          errorMessage = typeof errorBody.detail === 'string' ? errorBody.detail : JSON.stringify(errorBody.detail);
        } else if (errorBody.error && errorBody.error.message) {
          errorMessage = errorBody.error.message;
          errorCode = errorBody.error.code || errorCode;
        } else if (errorBody.message) {
          errorMessage = errorBody.message;
        }
      } else {
        const text = await response.text();
        if (text) {
          errorMessage = text.slice(0, 300);
        }
      }
    } catch {
      // Ignore parsing errors, keep default message
    }

    throw new ApiError(errorMessage, response.status, errorCode, details);
  }

  // Handle binary or JSON response
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  return response as unknown as T;
}

// ---------------------------------------------------------------------------
// Dedicated API Methods
// ---------------------------------------------------------------------------

export const apiClient = {
  /**
   * Health check for Python FastAPI backend.
   */
  async checkHealth(): Promise<HealthCheckResponse> {
    return request<HealthCheckResponse>('/api/health', {
      method: 'GET',
    });
  },

  /**
   * Analyzes raw academic text structure without transforming it.
   */
  async analyzeDocument(payload: DocumentProcessRequest): Promise<DocumentAnalysis> {
    return request<DocumentAnalysis>('/api/document/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Runs the full document processing pipeline:
   * Raw Input → Content Analysis → Content Cleanup → Structure Detection → Formatting Rules → Document Model
   */
  async processDocument(payload: DocumentProcessRequest): Promise<DocumentProcessResponse> {
    return request<DocumentProcessResponse>('/api/document/process', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Generates and downloads a Microsoft Word (.docx) document binary.
   */
  async exportDocx(payload: DocumentExportRequest): Promise<Blob> {
    const baseUrl = getBackendBaseUrl();
    const url = `${baseUrl}/api/documents/docx`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      },
      body: JSON.stringify({
        document: payload.document,
        raw_text: payload.raw_text,
        preset: payload.preset,
        filename: payload.filename,
        options: payload.options,
      }),
    });

    if (!response.ok) {
      let errorMsg = `DOCX export failed with status ${response.status}`;
      try {
        const json = await response.json();
        errorMsg = json.detail || json.message || errorMsg;
      } catch {
        // use fallback
      }
      throw new ApiError(errorMsg, response.status, 'DOCX_EXPORT_FAILED');
    }

    return await response.blob();
  },

  /**
   * Generates and downloads an Adobe PDF (.pdf) document binary.
   */
  async exportPdf(payload: DocumentExportRequest): Promise<Blob> {
    const baseUrl = getBackendBaseUrl();
    const url = `${baseUrl}/api/documents/pdf`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/pdf',
      },
      body: JSON.stringify({
        document: payload.document,
        raw_text: payload.raw_text,
        preset: payload.preset,
        filename: payload.filename,
        options: payload.options,
      }),
    });

    if (!response.ok) {
      let errorMsg = `PDF export failed with status ${response.status}`;
      try {
        const json = await response.json();
        errorMsg = json.detail || json.message || errorMsg;
      } catch {
        // use fallback
      }
      throw new ApiError(errorMsg, response.status, 'PDF_EXPORT_FAILED');
    }

    return await response.blob();
  },

  /**
   * AI text generation via configured AI provider (e.g., Google Gemini, Groq, OpenRouter, etc.).
   */
  async generateAI(payload: AIGenerateRequest): Promise<AIGenerateResponse> {
    return request<AIGenerateResponse>('/api/ai/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Lists all integrated AI providers, their availability, enabled state, and models.
   */
  async listProviders(): Promise<AIProviderManifestItem[]> {
    return request<AIProviderManifestItem[]>('/api/ai/providers', {
      method: 'GET',
    });
  },

  /**
   * Discovers models dynamically from a specific provider.
   */
  async discoverModels(providerId: string): Promise<any[]> {
    return request<any[]>(`/api/ai/providers/${providerId}/models`, {
      method: 'GET',
    });
  },

  /**
   * Validates credentials and connection for an AI provider.
   */
  async validateProvider(
    providerId: string,
    apiKey?: string,
    baseUrl?: string
  ): Promise<ProviderValidationResult> {
    return request<ProviderValidationResult>(`/api/ai/providers/${providerId}/validate`, {
      method: 'POST',
      body: JSON.stringify({
        api_key: apiKey,
        base_url: baseUrl,
      }),
    });
  },

  /**
   * Enables or disables an AI provider adapter.
   */
  async toggleProvider(
    providerId: string,
    enabled: boolean
  ): Promise<{ success: boolean; provider_id: string; enabled: boolean; message: string }> {
    return request(`/api/ai/providers/${providerId}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  },

  /**
   * Lists all registered modular document-processing skills.
   */
  async listSkills(): Promise<SkillInfo[]> {
    try {
      return await request<SkillInfo[]>('/api/skills', {
        method: 'GET',
      });
    } catch {
      return DEFAULT_SKILL_MANIFEST;
    }
  },

  /**
   * Validates a text snippet with a specific skill.
   */
  async validateSkill(
    skillId: string,
    text: string,
    context?: Record<string, unknown>
  ): Promise<SkillValidationResult> {
    return request<SkillValidationResult>(`/api/skills/${skillId}/validate`, {
      method: 'POST',
      body: JSON.stringify({ text, context }),
    });
  },

  /**
   * Transforms text through a single modular skill.
   */
  async processSkill(
    skillId: string,
    text: string,
    context?: Record<string, unknown>
  ): Promise<SkillExecutionResult> {
    return request<SkillExecutionResult>(`/api/skills/${skillId}/process`, {
      method: 'POST',
      body: JSON.stringify({ text, context }),
    });
  },
};
