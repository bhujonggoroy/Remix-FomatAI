import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
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
import { settingsStorage } from '../services/settingsStorage.ts';
import { AIProvider } from '../types/ai.ts';
import { SKILL_PRESETS, SkillPresetType } from '../types/skills.ts';

interface UserSettingsContextValue {
  // Current active profile state
  profile: UserProfileData;
  activeProfileId: string;
  allProfiles: { id: string; name: string; updatedAt: number }[];

  // Security Metadata
  securityMeta: StorageSecurityMeta;

  // AI & Provider Actions
  updateAISettings: (partial: Partial<UserAISettings>) => void;
  setApiKey: (provider: AIProvider, key: string) => void;
  getApiKey: (provider: AIProvider) => string;
  removeApiKey: (provider: AIProvider) => void;
  toggleProvider: (provider: AIProvider, enabled: boolean) => void;
  isProviderEnabled: (provider: AIProvider) => boolean;
  selectProvider: (provider: AIProvider) => void;
  selectModel: (provider: AIProvider, model: string) => void;
  setCustomBaseUrl: (provider: string, url: string) => void;

  // Formatting & Preferences Actions
  updateFormattingPreferences: (partial: Partial<UserFormattingPreferences>) => void;
  updateDocumentPreferences: (partial: Partial<UserDocumentPreferences>) => void;
  updateUIPreferences: (partial: Partial<UserUIPreferences>) => void;
  updateSkillPreferences: (partial: Partial<UserSkillPreferences>) => void;

  // Skills Management Actions
  activeSkills: string[];
  toggleSkill: (skillId: string, enabled: boolean) => void;
  isSkillEnabled: (skillId: string) => boolean;
  setSkillPreset: (presetKey: SkillPresetType) => void;

  // Profile Management Actions
  switchProfile: (profileId: string) => void;
  createProfile: (name: string) => void;
  deleteProfile: (profileId: string) => void;
  purgeAllSettings: () => void;
  exportSettings: (includeSecrets?: boolean) => string;
  importSettings: (jsonString: string) => void;
}

const UserSettingsContext = createContext<UserSettingsContextValue | null>(null);

export const UserSettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [store, setStore] = useState<UserSettingsStore>(() => settingsStorage.loadStore());

  // Listen to cross-tab storage changes on the same origin
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'formatai_v2_user_settings' && e.newValue) {
        try {
          const updated = settingsStorage.loadStore();
          setStore(updated);
        } catch {
          // ignore
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const activeProfile = store.profiles[store.activeProfileId] || Object.values(store.profiles)[0];

  const updateProfile = useCallback((updater: (prev: UserProfileData) => UserProfileData) => {
    const updated = settingsStorage.updateActiveProfile(updater);
    setStore(settingsStorage.loadStore());
    return updated;
  }, []);

  // AI & Provider Handlers
  const updateAISettings = useCallback(
    (partial: Partial<UserAISettings>) => {
      updateProfile((prev) => ({
        ...prev,
        ai: {
          ...prev.ai,
          ...partial,
        },
      }));
    },
    [updateProfile]
  );

  const setApiKey = useCallback(
    (provider: AIProvider, key: string) => {
      updateProfile((prev) => {
        const nextKeys = { ...prev.ai.apiKeys };
        if (key.trim()) {
          nextKeys[provider] = key.trim();
        } else {
          delete nextKeys[provider];
        }
        return {
          ...prev,
          ai: {
            ...prev.ai,
            apiKeys: nextKeys,
          },
        };
      });
    },
    [updateProfile]
  );

  const getApiKey = useCallback(
    (provider: AIProvider): string => {
      return activeProfile?.ai?.apiKeys?.[provider] || '';
    },
    [activeProfile]
  );

  const removeApiKey = useCallback(
    (provider: AIProvider) => {
      setApiKey(provider, '');
    },
    [setApiKey]
  );

  const toggleProvider = useCallback(
    (provider: AIProvider, enabled: boolean) => {
      updateProfile((prev) => ({
        ...prev,
        ai: {
          ...prev.ai,
          enabledProviders: {
            ...prev.ai.enabledProviders,
            [provider]: enabled,
          },
        },
      }));
    },
    [updateProfile]
  );

  const isProviderEnabled = useCallback(
    (provider: AIProvider): boolean => {
      if (activeProfile?.ai?.enabledProviders && provider in activeProfile.ai.enabledProviders) {
        return Boolean(activeProfile.ai.enabledProviders[provider]);
      }
      return true;
    },
    [activeProfile]
  );

  const selectProvider = useCallback(
    (provider: AIProvider) => {
      updateProfile((prev) => ({
        ...prev,
        ai: {
          ...prev.ai,
          selectedProvider: provider,
        },
      }));
    },
    [updateProfile]
  );

  const selectModel = useCallback(
    (provider: AIProvider, model: string) => {
      updateProfile((prev) => ({
        ...prev,
        ai: {
          ...prev.ai,
          selectedModel: {
            ...prev.ai.selectedModel,
            [provider]: model,
          },
        },
      }));
    },
    [updateProfile]
  );

  const setCustomBaseUrl = useCallback(
    (provider: string, url: string) => {
      updateProfile((prev) => ({
        ...prev,
        ai: {
          ...prev.ai,
          customBaseUrls: {
            ...prev.ai.customBaseUrls,
            [provider]: url,
          },
        },
      }));
    },
    [updateProfile]
  );

  // Formatting & Preferences Handlers
  const updateFormattingPreferences = useCallback(
    (partial: Partial<UserFormattingPreferences>) => {
      updateProfile((prev) => ({
        ...prev,
        formatting: {
          ...prev.formatting,
          ...partial,
        },
      }));
    },
    [updateProfile]
  );

  const updateDocumentPreferences = useCallback(
    (partial: Partial<UserDocumentPreferences>) => {
      updateProfile((prev) => ({
        ...prev,
        document: {
          ...prev.document,
          ...partial,
        },
      }));
    },
    [updateProfile]
  );

  const updateUIPreferences = useCallback(
    (partial: Partial<UserUIPreferences>) => {
      updateProfile((prev) => ({
        ...prev,
        ui: {
          ...prev.ui,
          ...partial,
        },
      }));
    },
    [updateProfile]
  );

  const updateSkillPreferences = useCallback(
    (partial: Partial<UserSkillPreferences>) => {
      updateProfile((prev) => ({
        ...prev,
        skills: {
          ...prev.skills,
          ...partial,
        },
      }));
    },
    [updateProfile]
  );

  // Skill Management Handlers
  const activeSkills = activeProfile?.skills?.activeSkills || [];

  const isSkillEnabled = useCallback(
    (skillId: string): boolean => {
      const skills = activeProfile?.skills?.activeSkills;
      if (!skills || !Array.isArray(skills)) return true;
      return skills.includes(skillId);
    },
    [activeProfile]
  );

  const toggleSkill = useCallback(
    (skillId: string, enabled: boolean) => {
      updateProfile((prev) => {
        const current = prev.skills?.activeSkills || [];
        const next = enabled
          ? Array.from(new Set([...current, skillId]))
          : current.filter((s) => s !== skillId);
        return {
          ...prev,
          skills: {
            ...prev.skills,
            activeSkills: next,
          },
        };
      });
    },
    [updateProfile]
  );

  const setSkillPreset = useCallback(
    (presetKey: SkillPresetType) => {
      const preset = SKILL_PRESETS[presetKey];
      if (preset) {
        updateProfile((prev) => ({
          ...prev,
          skills: {
            ...prev.skills,
            activeSkills: [...preset.skillIds],
          },
        }));
      }
    },
    [updateProfile]
  );

  // Profile Management Handlers
  const switchProfile = useCallback((profileId: string) => {
    settingsStorage.switchProfile(profileId);
    setStore(settingsStorage.loadStore());
  }, []);

  const createProfile = useCallback((name: string) => {
    settingsStorage.createProfile(name);
    setStore(settingsStorage.loadStore());
  }, []);

  const deleteProfile = useCallback((profileId: string) => {
    settingsStorage.deleteProfile(profileId);
    setStore(settingsStorage.loadStore());
  }, []);

  const purgeAllSettings = useCallback(() => {
    const fresh = settingsStorage.purgeAll();
    setStore(fresh);
  }, []);

  const exportSettings = useCallback((includeSecrets: boolean = false) => {
    return settingsStorage.exportSettings(includeSecrets);
  }, []);

  const importSettings = useCallback((jsonString: string) => {
    const updated = settingsStorage.importSettings(jsonString);
    setStore(updated);
  }, []);

  const allProfiles = Object.values(store.profiles).map((p) => ({
    id: p.id,
    name: p.name,
    updatedAt: p.updatedAt,
  }));

  const securityMeta = settingsStorage.getSecurityMeta();

  const value: UserSettingsContextValue = {
    profile: activeProfile,
    activeProfileId: store.activeProfileId,
    allProfiles,
    securityMeta,

    updateAISettings,
    setApiKey,
    getApiKey,
    removeApiKey,
    toggleProvider,
    isProviderEnabled,
    selectProvider,
    selectModel,
    setCustomBaseUrl,

    updateFormattingPreferences,
    updateDocumentPreferences,
    updateUIPreferences,
    updateSkillPreferences,

    activeSkills,
    toggleSkill,
    isSkillEnabled,
    setSkillPreset,

    switchProfile,
    createProfile,
    deleteProfile,
    purgeAllSettings,
    exportSettings,
    importSettings,
  };

  return <UserSettingsContext.Provider value={value}>{children}</UserSettingsContext.Provider>;
};

export function useUserSettings(): UserSettingsContextValue {
  const ctx = useContext(UserSettingsContext);
  if (!ctx) {
    throw new Error('useUserSettings must be used within a UserSettingsProvider');
  }
  return ctx;
}
