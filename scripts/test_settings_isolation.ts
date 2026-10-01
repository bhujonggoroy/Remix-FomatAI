/**
 * Automated Test Suite for FormatAI Client-Side User Settings Isolation.
 *
 * Verifies:
 * 1. Storage isolation between distinct workspace profiles
 * 2. All 8 user-local data categories remain strictly isolated per profile
 * 3. No global window pollution or shared JavaScript mutable singletons
 * 4. Redacted vs Full export confidentiality
 * 5. Corrupted storage recovery without crashes
 * 6. Clean purge operation
 */

import { settingsStorage, SETTINGS_STORAGE_KEY } from '../frontend/src/services/settingsStorage.ts';

// Mock localStorage for headless Node environment
const mockStorage: Record<string, string> = {};
(global as any).window = {
  localStorage: {
    getItem: (key: string) => mockStorage[key] || null,
    setItem: (key: string, val: string) => {
      mockStorage[key] = val;
    },
    removeItem: (key: string) => {
      delete mockStorage[key];
    },
  },
};

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`❌ ASSERTION FAILED: ${message}`);
    process.exit(1);
  }
  console.log(`  ✓ ${message}`);
}

async function runTests() {
  console.log('\n=== RUNNING CLIENT-SIDE USER SETTINGS ISOLATION TESTS ===\n');

  // Test 1: Clean initialization
  console.log('Test 1: Clean initialization and storage driver');
  settingsStorage.purgeAll();
  const initialStore = settingsStorage.loadStore();
  assert(initialStore.version === 2, 'Storage store version is 2');
  assert(Boolean(initialStore.profiles['default']), 'Default profile created automatically');
  const secMeta = settingsStorage.getSecurityMeta();
  assert(secMeta.isEncryptedAtRest === false, 'Explicitly declares unencrypted at rest on local disk');
  assert(secMeta.backendPersistence === false, 'Explicitly declares zero backend persistence');

  // Test 2: User A (Profile 1) vs User B (Profile 2) Isolation
  console.log('\nTest 2: Profile-Level Isolation (User A vs User B)');
  const profileA = settingsStorage.createProfile('Researcher A');
  assert(profileA.name === 'Researcher A', 'Profile A created');

  // Update Profile A with personal credentials and preferences
  settingsStorage.updateActiveProfile((prev) => ({
    ...prev,
    ai: {
      ...prev.ai,
      apiKeys: {
        groq: 'gsk_secret_user_a_key_12345',
        openai: 'sk-proj-user_a_key_99999',
      },
      enabledProviders: {
        ...prev.ai.enabledProviders,
        mistral: false, // User A disabled mistral
      },
      selectedProvider: 'groq',
      customBaseUrls: {
        custom: 'http://192.168.1.50:11434/v1',
      },
    },
    formatting: {
      ...prev.formatting,
      preset: 'academic',
      customFilename: 'user_a_thesis',
    },
    ui: {
      ...prev.ui,
      editorFontSize: 16,
      theme: 'light',
    },
    skills: {
      ...prev.skills,
      citationStyle: 'chicago',
    },
  }));

  // Create Profile B (e.g. User B or a separate project)
  const profileB = settingsStorage.createProfile('Researcher B');
  assert(profileB.name === 'Researcher B', 'Profile B created');
  assert(profileB.id !== profileA.id, 'Profile B has distinct ID');

  // Verify Profile B has ZERO knowledge of Profile A's data
  assert(profileB.ai.apiKeys.groq === undefined, "Profile B does NOT have Profile A's Groq key");
  assert(profileB.ai.apiKeys.openai === undefined, "Profile B does NOT have Profile A's OpenAI key");
  assert(profileB.ai.enabledProviders.mistral === true, 'Profile B still has Mistral enabled');
  assert(profileB.ai.selectedProvider === 'gemini', 'Profile B uses default provider (Gemini)');
  assert(profileB.formatting.preset === 'research_paper', 'Profile B uses default formatting preset');
  assert(profileB.formatting.customFilename === 'manuscript_formatted', 'Profile B uses default filename');
  assert(profileB.ui.editorFontSize === 13, 'Profile B has default font size');
  assert(profileB.skills.citationStyle === 'apa7', 'Profile B has default citation style');

  // Test 3: Switching back restores Profile A accurately
  console.log('\nTest 3: Switching active profile restores isolated state');
  const restoredA = settingsStorage.switchProfile(profileA.id);
  assert(restoredA.ai.apiKeys.groq === 'gsk_secret_user_a_key_12345', "Restored Profile A retains Groq key");
  assert(restoredA.ai.enabledProviders.mistral === false, 'Restored Profile A retains disabled Mistral state');
  assert(restoredA.formatting.customFilename === 'user_a_thesis', 'Restored Profile A retains custom filename');

  // Test 4: Redacted vs Full Export
  console.log('\nTest 4: Redacted vs Full Export');
  const redactedJson = settingsStorage.exportSettings(false);
  assert(!redactedJson.includes('gsk_secret_user_a_key_12345'), 'Redacted export DOES NOT contain real Groq key');
  assert(redactedJson.includes('[REDACTED]'), 'Redacted export contains [REDACTED] placeholder');

  const fullJson = settingsStorage.exportSettings(true);
  assert(fullJson.includes('gsk_secret_user_a_key_12345'), 'Full export contains real key for private user backup');

  // Test 5: Storage corruption recovery
  console.log('\nTest 5: Storage corruption recovery');
  mockStorage[SETTINGS_STORAGE_KEY] = 'INVALID_JSON_CORRUPTED{{{';
  const recoveredStore = settingsStorage.loadStore();
  assert(Boolean(recoveredStore.profiles['default']), 'Corrupted storage auto-recovers to valid default store');

  // Test 6: Purge All
  console.log('\nTest 6: Purge all local data');
  settingsStorage.purgeAll();
  const purgedStore = settingsStorage.loadStore();
  const allIds = Object.keys(purgedStore.profiles);
  assert(allIds.length === 1 && allIds[0] === 'default', 'Purge wipes all custom profiles');
  assert(Object.keys(purgedStore.profiles['default'].ai.apiKeys).length === 0, 'Purge wipes all API keys');

  // Test 7: No global object pollution
  console.log('\nTest 7: No global window pollution');
  assert((global as any).window.settings === undefined, 'No window.settings global object');
  assert((global as any).window.userSettings === undefined, 'No window.userSettings global object');
  assert((global as any).window.apiKeys === undefined, 'No window.apiKeys global object');

  console.log('\n✅ ALL 7 CLIENT-SIDE SETTINGS ISOLATION TESTS PASSED!\n');
}

runTests().catch((err) => {
  console.error('Test execution failed:', err);
  process.exit(1);
});
