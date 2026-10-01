import { AIProvider } from './ai.ts';
import { DocumentProcessingOptions, StylePresetName } from './document.ts';

/**
 * AI Provider settings scoped strictly to the client browser instance/profile.
 */
export interface UserAISettings {
  apiKeys: Partial<Record<AIProvider, string>>;
  enabledProviders: Record<AIProvider, boolean>;
  selectedProvider: AIProvider;
  selectedModel: Record<AIProvider, string>;
  customBaseUrls: Record<string, string>;
  temperature: number;
  timeoutSeconds: number;
  fallbackProvider: string;
}

/**
 * Academic formatting preferences scoped strictly to the client browser instance/profile.
 */
export interface UserFormattingPreferences {
  preset: StylePresetName;
  options: DocumentProcessingOptions;
  customFilename: string;
}

/**
 * Document workflow preferences scoped strictly to the client browser instance/profile.
 */
export interface UserDocumentPreferences {
  defaultExportFormat: 'docx' | 'pdf';
  autoFormatOnPaste: boolean;
  maxHistoryItems: number;
  preserveRawInput: boolean;
}

/**
 * UI layout and presentation preferences scoped strictly to the client browser instance/profile.
 */
export interface UserUIPreferences {
  theme: 'dark' | 'light' | 'system';
  previewLayout: 'split' | 'tabs';
  showLiveStats: boolean;
  editorFontSize: number;
  mathRenderingMode: 'katex' | 'raw';
}

/**
 * Academic skill preferences (tone, citation style, strictness) scoped strictly to the client browser instance/profile.
 */
export interface UserSkillPreferences {
  scholarlyTone: 'rigorous' | 'balanced' | 'introductory';
  citationStyle: 'apa7' | 'ieee' | 'chicago' | 'mla9';
  mathStrictness: 'strict_latex' | 'flexible';
  activeSkills: string[];
}

/**
 * Isolated profile data partition.
 */
export interface UserProfileData {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  ai: UserAISettings;
  formatting: UserFormattingPreferences;
  document: UserDocumentPreferences;
  ui: UserUIPreferences;
  skills: UserSkillPreferences;
}

/**
 * Master client-local settings payload stored in browser storage.
 */
export interface UserSettingsStore {
  version: number;
  activeProfileId: string;
  profiles: Record<string, UserProfileData>;
  lastPurgedAt?: number;
}

/**
 * Metadata clarifying the browser storage security and isolation model.
 */
export interface StorageSecurityMeta {
  storageMechanism: 'localStorage' | 'sessionStorage' | 'inMemory';
  isIsolatedByOrigin: boolean;
  isEncryptedAtRest: boolean; // Explicitly false for standard browser localStorage
  hasAccessToOtherProfiles: boolean; // Explicitly false
  backendPersistence: boolean; // Explicitly false
}
