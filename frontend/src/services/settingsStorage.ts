import {
  StorageSecurityMeta,
  UserAISettings,
  UserDocumentPreferences,
  UserFormattingPreferences,
  UserProfileData,
  UserSettingsStore,
  UserSkillPreferences,
  UserUIPreferences,
} from '../types/settings.ts';
import { DEFAULT_PROCESSING_OPTIONS } from './documentService.ts';

export const SETTINGS_STORAGE_KEY = 'formatai_v2_user_settings';
export const CURRENT_SETTINGS_VERSION = 2;

// In-memory fallback if browser localStorage is blocked or unavailable
let memoryStorage: Record<string, string> = {};

/**
 * Storage driver abstraction: checks if window.localStorage is accessible and writable.
 */
function getStorageDriver(): {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
  type: 'localStorage' | 'inMemory';
} {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const testKey = '__formatai_test__';
      window.localStorage.setItem(testKey, '1');
      window.localStorage.removeItem(testKey);
      return {
        getItem: (k) => window.localStorage.getItem(k),
        setItem: (k, v) => window.localStorage.setItem(k, v),
        removeItem: (k) => window.localStorage.removeItem(k),
        type: 'localStorage',
      };
    }
  } catch {
    // Falls through to in-memory fallback
  }

  return {
    getItem: (k) => memoryStorage[k] || null,
    setItem: (k, v) => {
      memoryStorage[k] = v;
    },
    removeItem: (k) => {
      delete memoryStorage[k];
    },
    type: 'inMemory',
  };
}

export const DEFAULT_AI_SETTINGS: UserAISettings = {
  apiKeys: {},
  enabledProviders: {
    gemini: true,
    groq: true,
    openrouter: true,
    mistral: true,
    cohere: true,
    huggingface: true,
    openai: true,
    custom: true,
  },
  selectedProvider: 'gemini',
  selectedModel: {
    gemini: 'gemini-3.8-flash',
    groq: 'llama-3.3-70b-versatile',
    openrouter: 'meta-llama/llama-3.3-70b-instruct',
    mistral: 'mistral-small-latest',
    cohere: 'command-r-plus-08-2024',
    huggingface: 'Qwen/Qwen2.5-72B-Instruct',
    openai: 'gpt-4o',
    custom: 'custom-model',
  },
  customBaseUrls: {
    custom: 'http://localhost:11434/v1',
  },
  temperature: 0.2,
  timeoutSeconds: 30,
  fallbackProvider: '',
};

export const DEFAULT_FORMATTING_PREFERENCES: UserFormattingPreferences = {
  preset: 'research_paper',
  options: { ...DEFAULT_PROCESSING_OPTIONS },
  customFilename: 'manuscript_formatted',
};

export const DEFAULT_DOCUMENT_PREFERENCES: UserDocumentPreferences = {
  defaultExportFormat: 'docx',
  autoFormatOnPaste: false,
  maxHistoryItems: 10,
  preserveRawInput: true,
};

export const DEFAULT_UI_PREFERENCES: UserUIPreferences = {
  theme: 'dark',
  previewLayout: 'split',
  showLiveStats: true,
  editorFontSize: 13,
  mathRenderingMode: 'katex',
};

export const DEFAULT_ACTIVE_SKILLS = [
  'markdown_cleanup',
  'academic_formatting',
  'mathematics',
  'statistics',
  'chemistry',
  'tables',
  'citation_references',
  'exam_questions',
  'study_notes',
  'scientific_document',
];

export const DEFAULT_SKILL_PREFERENCES: UserSkillPreferences = {
  scholarlyTone: 'rigorous',
  citationStyle: 'apa7',
  mathStrictness: 'strict_latex',
  activeSkills: [...DEFAULT_ACTIVE_SKILLS],
};

export function createDefaultProfile(id: string = 'default', name: string = 'Default Workspace'): UserProfileData {
  const now = Date.now();
  return {
    id,
    name,
    createdAt: now,
    updatedAt: now,
    ai: JSON.parse(JSON.stringify(DEFAULT_AI_SETTINGS)),
    formatting: JSON.parse(JSON.stringify(DEFAULT_FORMATTING_PREFERENCES)),
    document: JSON.parse(JSON.stringify(DEFAULT_DOCUMENT_PREFERENCES)),
    ui: JSON.parse(JSON.stringify(DEFAULT_UI_PREFERENCES)),
    skills: JSON.parse(JSON.stringify(DEFAULT_SKILL_PREFERENCES)),
  };
}

export function createInitialStore(): UserSettingsStore {
  const defaultProfile = createDefaultProfile();
  return {
    version: CURRENT_SETTINGS_VERSION,
    activeProfileId: defaultProfile.id,
    profiles: {
      [defaultProfile.id]: defaultProfile,
    },
  };
}

/**
 * Validates and deep-merges profile data to guarantee missing or newly introduced fields
 * always have default values without crashing.
 */
function sanitizeProfileData(raw: any, fallbackId: string): UserProfileData {
  const fallback = createDefaultProfile(fallbackId, raw?.name || 'Academic Profile');
  if (!raw || typeof raw !== 'object') return fallback;

  return {
    id: typeof raw.id === 'string' && raw.id.trim() ? raw.id.trim() : fallbackId,
    name: typeof raw.name === 'string' && raw.name.trim() ? raw.name.trim() : fallback.name,
    createdAt: typeof raw.createdAt === 'number' ? raw.createdAt : fallback.createdAt,
    updatedAt: typeof raw.updatedAt === 'number' ? raw.updatedAt : Date.now(),
    ai: {
      apiKeys: raw.ai?.apiKeys && typeof raw.ai.apiKeys === 'object' ? raw.ai.apiKeys : {},
      enabledProviders: {
        ...DEFAULT_AI_SETTINGS.enabledProviders,
        ...(raw.ai?.enabledProviders || {}),
      },
      selectedProvider: raw.ai?.selectedProvider || DEFAULT_AI_SETTINGS.selectedProvider,
      selectedModel: {
        ...DEFAULT_AI_SETTINGS.selectedModel,
        ...(raw.ai?.selectedModel || {}),
      },
      customBaseUrls: {
        ...DEFAULT_AI_SETTINGS.customBaseUrls,
        ...(raw.ai?.customBaseUrls || {}),
      },
      temperature: typeof raw.ai?.temperature === 'number' ? raw.ai.temperature : DEFAULT_AI_SETTINGS.temperature,
      timeoutSeconds: typeof raw.ai?.timeoutSeconds === 'number' ? raw.ai.timeoutSeconds : DEFAULT_AI_SETTINGS.timeoutSeconds,
      fallbackProvider: typeof raw.ai?.fallbackProvider === 'string' ? raw.ai.fallbackProvider : '',
    },
    formatting: {
      preset: raw.formatting?.preset || DEFAULT_FORMATTING_PREFERENCES.preset,
      options: {
        ...DEFAULT_FORMATTING_PREFERENCES.options,
        ...(raw.formatting?.options || {}),
      },
      customFilename: raw.formatting?.customFilename || DEFAULT_FORMATTING_PREFERENCES.customFilename,
    },
    document: {
      ...DEFAULT_DOCUMENT_PREFERENCES,
      ...(raw.document || {}),
    },
    ui: {
      ...DEFAULT_UI_PREFERENCES,
      ...(raw.ui || {}),
    },
    skills: {
      ...DEFAULT_SKILL_PREFERENCES,
      ...(raw.skills || {}),
    },
  };
}

export const settingsStorage = {
  /**
   * Returns current storage driver metadata and security characteristics.
   */
  getSecurityMeta(): StorageSecurityMeta {
    const driver = getStorageDriver();
    return {
      storageMechanism: driver.type,
      isIsolatedByOrigin: true,
      isEncryptedAtRest: false, // Explicit: browser localStorage is plaintext at rest on user machine
      hasAccessToOtherProfiles: false,
      backendPersistence: false, // Explicit: never sent or stored on backend database
    };
  },

  /**
   * Loads the user settings store from client browser storage.
   * Auto-repairs corrupted entries and migrates legacy schemas.
   */
  loadStore(): UserSettingsStore {
    const driver = getStorageDriver();
    try {
      const raw = driver.getItem(SETTINGS_STORAGE_KEY);
      if (!raw) {
        const initial = createInitialStore();
        this.saveStore(initial);
        return initial;
      }

      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || !parsed.profiles) {
        const fallback = createInitialStore();
        this.saveStore(fallback);
        return fallback;
      }

      const sanitizedProfiles: Record<string, UserProfileData> = {};
      for (const [id, pData] of Object.entries(parsed.profiles)) {
        sanitizedProfiles[id] = sanitizeProfileData(pData, id);
      }

      const activeId =
        typeof parsed.activeProfileId === 'string' && sanitizedProfiles[parsed.activeProfileId]
          ? parsed.activeProfileId
          : Object.keys(sanitizedProfiles)[0] || 'default';

      if (!sanitizedProfiles[activeId]) {
        const def = createDefaultProfile('default');
        sanitizedProfiles['default'] = def;
      }

      const store: UserSettingsStore = {
        version: CURRENT_SETTINGS_VERSION,
        activeProfileId: activeId,
        profiles: sanitizedProfiles,
        lastPurgedAt: parsed.lastPurgedAt,
      };

      return store;
    } catch (err) {
      console.warn('[FormatAI] Settings storage read failed, initializing safe defaults:', err);
      const initial = createInitialStore();
      this.saveStore(initial);
      return initial;
    }
  },

  /**
   * Writes the user settings store to browser storage.
   */
  saveStore(store: UserSettingsStore): void {
    const driver = getStorageDriver();
    try {
      driver.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(store));
    } catch (err) {
      console.error('[FormatAI] Failed to write settings to browser storage (quota exceeded or blocked):', err);
    }
  },

  /**
   * Retrieves the currently active user profile.
   */
  getActiveProfile(): UserProfileData {
    const store = this.loadStore();
    return store.profiles[store.activeProfileId] || createDefaultProfile();
  },

  /**
   * Updates fields within the active profile and persists to browser storage.
   */
  updateActiveProfile(updater: (prev: UserProfileData) => UserProfileData): UserProfileData {
    const store = this.loadStore();
    const current = store.profiles[store.activeProfileId] || createDefaultProfile(store.activeProfileId);
    const updated = updater(current);
    updated.updatedAt = Date.now();
    store.profiles[store.activeProfileId] = updated;
    this.saveStore(store);
    return updated;
  },

  /**
   * Switches the active profile in browser storage.
   */
  switchProfile(profileId: string): UserProfileData {
    const store = this.loadStore();
    if (!store.profiles[profileId]) {
      throw new Error(`Profile '${profileId}' does not exist.`);
    }
    store.activeProfileId = profileId;
    this.saveStore(store);
    return store.profiles[profileId];
  },

  /**
   * Creates a new isolated profile.
   */
  createProfile(name: string): UserProfileData {
    const store = this.loadStore();
    const id = `profile_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const newProfile = createDefaultProfile(id, name.trim() || 'New Workspace');
    store.profiles[id] = newProfile;
    store.activeProfileId = id;
    this.saveStore(store);
    return newProfile;
  },

  /**
   * Deletes a profile. Active profile switches to first remaining profile.
   */
  deleteProfile(profileId: string): UserSettingsStore {
    const store = this.loadStore();
    const keys = Object.keys(store.profiles);
    if (keys.length <= 1) {
      throw new Error('Cannot delete the only existing workspace profile.');
    }

    delete store.profiles[profileId];
    if (store.activeProfileId === profileId) {
      store.activeProfileId = Object.keys(store.profiles)[0];
    }

    this.saveStore(store);
    return store;
  },

  /**
   * Purges all user settings, API keys, and profiles from browser storage.
   */
  purgeAll(): UserSettingsStore {
    const driver = getStorageDriver();
    driver.removeItem(SETTINGS_STORAGE_KEY);
    memoryStorage = {};
    const fresh = createInitialStore();
    fresh.lastPurgedAt = Date.now();
    this.saveStore(fresh);
    return fresh;
  },

  /**
   * Exports settings to a portable JSON backup.
   * If includeSecrets is false, all API keys are replaced with "[REDACTED]".
   */
  exportSettings(includeSecrets: boolean = false): string {
    const store = this.loadStore();
    const cloned: UserSettingsStore = JSON.parse(JSON.stringify(store));

    if (!includeSecrets) {
      for (const p of Object.values(cloned.profiles)) {
        if (p.ai && p.ai.apiKeys) {
          for (const prov of Object.keys(p.ai.apiKeys)) {
            p.ai.apiKeys[prov as keyof typeof p.ai.apiKeys] = '[REDACTED]';
          }
        }
      }
    }

    return JSON.stringify(
      {
        format: 'formatai_user_settings_backup',
        version: CURRENT_SETTINGS_VERSION,
        exportedAt: new Date().toISOString(),
        containsSecrets: includeSecrets,
        store: cloned,
      },
      null,
      2
    );
  },

  /**
   * Imports settings from a valid JSON backup string.
   */
  importSettings(jsonString: string): UserSettingsStore {
    const parsed = JSON.parse(jsonString);
    const storeData = parsed.store || parsed;

    if (!storeData || typeof storeData !== 'object' || !storeData.profiles) {
      throw new Error('Invalid FormatAI settings backup structure.');
    }

    const sanitizedProfiles: Record<string, UserProfileData> = {};
    for (const [id, pData] of Object.entries(storeData.profiles)) {
      const sanitized = sanitizeProfileData(pData, id);
      // If keys were redacted in backup, ignore "[REDACTED]"
      if (sanitized.ai && sanitized.ai.apiKeys) {
        for (const [k, v] of Object.entries(sanitized.ai.apiKeys)) {
          if (v === '[REDACTED]') {
            delete sanitized.ai.apiKeys[k as keyof typeof sanitized.ai.apiKeys];
          }
        }
      }
      sanitizedProfiles[id] = sanitized;
    }

    const activeId =
      typeof storeData.activeProfileId === 'string' && sanitizedProfiles[storeData.activeProfileId]
        ? storeData.activeProfileId
        : Object.keys(sanitizedProfiles)[0] || 'default';

    const mergedStore: UserSettingsStore = {
      version: CURRENT_SETTINGS_VERSION,
      activeProfileId: activeId,
      profiles: sanitizedProfiles,
    };

    this.saveStore(mergedStore);
    return mergedStore;
  },
};
