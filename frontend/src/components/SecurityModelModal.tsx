import React, { useState } from 'react';
import {
  Shield,
  ShieldCheck,
  Lock,
  EyeOff,
  Server,
  Trash2,
  Download,
  HardDrive,
  Copy,
  Check,
  X,
  AlertTriangle,
  FolderLock,
  Layers,
} from 'lucide-react';
import { useUserSettings } from '../hooks/useUserSettings.ts';

interface SecurityModelModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SecurityModelModal: React.FC<SecurityModelModalProps> = ({ isOpen, onClose }) => {
  const {
    activeProfileId,
    allProfiles,
    securityMeta,
    switchProfile,
    createProfile,
    deleteProfile,
    purgeAllSettings,
    exportSettings,
    importSettings,
  } = useUserSettings();

  const [activeTab, setActiveTab] = useState<'security_model' | 'storage_inspector' | 'profiles'>('security_model');
  const [copied, setCopied] = useState<boolean>(false);
  const [purgeConfirm, setPurgeConfirm] = useState<boolean>(false);
  const [newProfileName, setNewProfileName] = useState<string>('');
  const [importJsonText, setImportJsonText] = useState<string>('');
  const [importStatus, setImportStatus] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCopyRawStorage = () => {
    const exported = exportSettings(false);
    navigator.clipboard.writeText(exported);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadBackup = (includeSecrets: boolean) => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(exportSettings(includeSecrets));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute(
      'download',
      `formatai_settings_${includeSecrets ? 'full' : 'redacted'}_${Date.now()}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImport = () => {
    try {
      if (!importJsonText.trim()) return;
      importSettings(importJsonText);
      setImportStatus('Settings imported successfully.');
      setImportJsonText('');
      setTimeout(() => setImportStatus(null), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid JSON format';
      setImportStatus(`Import failed: ${msg}`);
    }
  };

  const handleCreateProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfileName.trim()) return;
    createProfile(newProfileName.trim());
    setNewProfileName('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-950/70 border border-indigo-800/80 text-indigo-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Client-Local Security & Privacy Architecture</h2>
              <p className="text-xs text-slate-400">
                FormatAI treats all user settings, API keys, and preferences as strictly client-local data.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('security_model')}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition cursor-pointer ${
              activeTab === 'security_model'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Security Model</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('profiles')}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition cursor-pointer ${
              activeTab === 'profiles'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Isolated Profiles ({allProfiles.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('storage_inspector')}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition cursor-pointer ${
              activeTab === 'storage_inspector'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <HardDrive className="w-4 h-4" />
            <span>Storage Inspector & Purge</span>
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-300 text-xs leading-relaxed">
          {activeTab === 'security_model' && (
            <div className="space-y-6">
              {/* Critical Security Distinction Banner */}
              <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/80 text-amber-200 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-amber-300 text-sm">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>Important Security Notice: Storage is Isolated, but Not Encrypted at Rest</span>
                </div>
                <p className="text-xs text-amber-200/90 leading-normal">
                  FormatAI stores your configuration in browser <code>localStorage</code>. While browser storage is
                  strictly <strong>isolated</strong> by domain and browser profile, it is{' '}
                  <strong>unencrypted plaintext at rest</strong> on your physical disk. Anyone with physical access to your
                  workstation or operating system user account can inspect these files. Do not store sensitive master keys on
                  shared or untrusted machines.
                </p>
              </div>

              {/* Four Pillars Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Pillar 1: Isolation */}
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                    <FolderLock className="w-4 h-4" />
                    <span>1. Isolation</span>
                  </div>
                  <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-[11px]">
                    <li>
                      <strong>Browser Origin:</strong> Bound strictly by Web Same-Origin Policy (SOP). Other websites cannot
                      read your FormatAI configuration.
                    </li>
                    <li>
                      <strong>Browser Profiles:</strong> Different profiles (e.g. Chrome Profile 1 vs Profile 2, or Firefox vs
                      Chrome) maintain separate storage partitions.
                    </li>
                    <li>
                      <strong>Stateless Backend:</strong> The backend has no database of users. User A cannot query or
                      receive User B’s settings because the server stores none.
                    </li>
                  </ul>
                </div>

                {/* Pillar 2: Confidentiality */}
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                    <Lock className="w-4 h-4" />
                    <span>2. Confidentiality</span>
                  </div>
                  <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-[11px]">
                    <li>
                      <strong>In Transit:</strong> All communication between browser and server uses TLS/HTTPS encryption,
                      protecting requests from network sniffing.
                    </li>
                    <li>
                      <strong>Scoped Delivery:</strong> API keys are only transmitted when an AI generation action is
                      explicitly triggered.
                    </li>
                    <li>
                      <strong>Per-Request Delivery:</strong> Keys are passed strictly in request payloads, never in query
                      strings or URLs.
                    </li>
                  </ul>
                </div>

                {/* Pillar 3: Encryption */}
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
                    <EyeOff className="w-4 h-4" />
                    <span>3. Encryption (At Rest)</span>
                  </div>
                  <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-[11px]">
                    <li>
                      <strong>Plaintext on Disk:</strong> Standard browser <code>localStorage</code> does NOT provide
                      cryptographic encryption on disk.
                    </li>
                    <li>
                      <strong>No False Claims:</strong> We never claim browser storage is a Hardware Security Module (HSM) or
                      vault.
                    </li>
                    <li>
                      <strong>Purge on Exit:</strong> Use the one-click "Purge All Data" button to cleanly erase all keys and
                      preferences before leaving shared hardware.
                    </li>
                  </ul>
                </div>

                {/* Pillar 4: Server-Side Exposure */}
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
                    <Server className="w-4 h-4" />
                    <span>4. Zero Server-Side Persistence</span>
                  </div>
                  <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-[11px]">
                    <li>
                      <strong>No Database Storage:</strong> The server never writes user API keys or settings to database,
                      disk, or cache.
                    </li>
                    <li>
                      <strong>Ephemeral RAM Only:</strong> Request parameters exist only for the microsecond duration of the
                      upstream call.
                    </li>
                    <li>
                      <strong>Log Sanitization:</strong> Server loggers automatically redact <code>sk-...</code>,{' '}
                      <code>Bearer ...</code>, and all credential patterns.
                    </li>
                  </ul>
                </div>
              </div>

              {/* Summary of Localized Data */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Guaranteed User-Local Data Inventory
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    🔑 Provider API Keys
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    🔌 Provider Enable/Disable
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    🎯 Selected Provider & Model
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    📐 Formatting Preferences
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    📄 Document Preset & Filename
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    🖥️ UI Layout & Font Preferences
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    ⚡ Scholarly Skill Settings
                  </span>
                  <span className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    🌐 Custom Endpoint URLs
                  </span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'profiles' && (
            <div className="space-y-6">
              <p className="text-xs text-slate-400">
                Profiles let you separate configurations for different projects (e.g. personal research vs. collaborative
                grants) on this device without sharing settings between them.
              </p>

              {/* Create Profile Form */}
              <form onSubmit={handleCreateProfile} className="flex gap-2">
                <input
                  type="text"
                  placeholder="New profile name (e.g., 'Journal Submission', 'Lab Project')"
                  value={newProfileName}
                  onChange={(e) => setNewProfileName(e.target.value)}
                  className="flex-1 bg-slate-950 border border-slate-800 text-xs text-white rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
                >
                  Create Profile
                </button>
              </form>

              {/* Profiles List */}
              <div className="space-y-2">
                {allProfiles.map((p) => {
                  const isActive = p.id === activeProfileId;
                  return (
                    <div
                      key={p.id}
                      className={`flex items-center justify-between p-3 rounded-xl border transition ${
                        isActive
                          ? 'bg-indigo-950/40 border-indigo-500/70'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-white">{p.name}</span>
                          {isActive && (
                            <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/40">
                              Active
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500">
                          Last modified: {new Date(p.updatedAt).toLocaleString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {!isActive && (
                          <button
                            type="button"
                            onClick={() => switchProfile(p.id)}
                            className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 transition cursor-pointer"
                          >
                            Switch
                          </button>
                        )}
                        {allProfiles.length > 1 && (
                          <button
                            type="button"
                            onClick={() => deleteProfile(p.id)}
                            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-950/40 transition cursor-pointer"
                            title="Delete profile"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'storage_inspector' && (
            <div className="space-y-6">
              {/* Storage Diagnostics */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Driver:</span>
                  <span className="font-mono text-emerald-400">{securityMeta.storageMechanism}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Encrypted At Rest:</span>
                  <span className="font-mono text-amber-400">No (Plaintext Disk)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Server Persistence:</span>
                  <span className="font-mono text-emerald-400">None (Client Only)</span>
                </div>
              </div>

              {/* Export & Import Actions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => handleDownloadBackup(false)}
                  className="flex items-center justify-center gap-2 p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-200 transition cursor-pointer"
                >
                  <Download className="w-4 h-4 text-indigo-400" />
                  <span>Download Redacted Backup (No Keys)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadBackup(true)}
                  className="flex items-center justify-center gap-2 p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-200 transition cursor-pointer"
                >
                  <Download className="w-4 h-4 text-amber-400" />
                  <span>Download Full Backup (Includes Keys)</span>
                </button>
              </div>

              {/* Import Section */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">Import Backup JSON</label>
                <textarea
                  rows={3}
                  value={importJsonText}
                  onChange={(e) => setImportJsonText(e.target.value)}
                  placeholder="Paste FormatAI backup JSON content here..."
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-[11px] font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={handleImport}
                    disabled={!importJsonText.trim()}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition cursor-pointer"
                  >
                    Import Settings
                  </button>
                  {importStatus && <span className="text-xs text-indigo-300">{importStatus}</span>}
                </div>
              </div>

              {/* Live JSON Inspector */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Current Active Configuration (Redacted Preview)
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyRawStorage}
                    className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                  </button>
                </div>
                <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-[10px] font-mono text-slate-300 overflow-x-auto max-h-48">
                  {exportSettings(false)}
                </pre>
              </div>

              {/* Dangerous Purge Action */}
              <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-900/60 space-y-3">
                <div className="flex items-center gap-2 text-rose-300 font-semibold text-xs">
                  <Trash2 className="w-4 h-4 text-rose-400" />
                  <span>Purge All Client Data & Reset</span>
                </div>
                <p className="text-[11px] text-rose-200/80">
                  Immediately erases all API keys, custom profiles, and formatting preferences from your browser
                  storage. This cannot be undone.
                </p>

                {purgeConfirm ? (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        purgeAllSettings();
                        setPurgeConfirm(false);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition cursor-pointer"
                    >
                      Confirm Erase All Data
                    </button>
                    <button
                      type="button"
                      onClick={() => setPurgeConfirm(false)}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs transition cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setPurgeConfirm(true)}
                    className="px-3 py-1.5 rounded-lg bg-rose-950/70 border border-rose-800 text-rose-300 hover:bg-rose-900/50 text-xs font-semibold transition cursor-pointer"
                  >
                    Purge All Local Settings
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>FormatAI Client-Local Settings Storage (Version 2)</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
