import React, { useState, useEffect } from 'react';
import { useUserSettings } from '../contexts/UserSettingsContext.tsx';
import { apiClient } from '../services/api.ts';
import { SkillInfo, SKILL_PRESETS, SkillPresetType, SkillExecutionResult } from '../types/skills.ts';

interface SkillsManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  executedSkills?: string[];
  skippedSkills?: string[];
}

export const SkillsManagerModal: React.FC<SkillsManagerModalProps> = ({
  isOpen,
  onClose,
  executedSkills = [],
  skippedSkills = [],
}) => {
  const { activeSkills, toggleSkill, setSkillPreset } = useUserSettings();

  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'catalog' | 'sandbox'>('catalog');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Sandbox state
  const [testSkillId, setTestSkillId] = useState<string>('chemistry');
  const [testInput, setTestInput] = useState<string>('Combustion: CH4 + 2 O2 -> CO2 + 2 H2O and Ca2+ ions.');
  const [testResult, setTestResult] = useState<SkillExecutionResult | null>(null);
  const [testLoading, setTestLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;
    setLoading(true);

    apiClient
      .listSkills()
      .then((data) => {
        if (isMounted) {
          setSkills(data);
          if (data.length > 0 && !testSkillId) {
            setTestSkillId(data[0].id);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load skills:', err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  // Handle ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredSkills = skills.filter((s) => {
    if (selectedCategory === 'all') return true;
    return s.category === selectedCategory;
  });

  const handleTestSkill = async () => {
    if (!testSkillId || !testInput.trim()) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await apiClient.processSkill(testSkillId, testInput);
      setTestResult(res);
    } catch (err: unknown) {
      console.error('Skill test failed:', err);
    } finally {
      setTestLoading(false);
    }
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'stem':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'editorial':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'formatting':
        return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
      default:
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                Modular Skills Architecture
                <span className="px-2 py-0.5 text-xs font-mono rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {activeSkills.length} / {skills.length} Active
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Independent document processing plugins executed in strict priority order.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Tabs */}
            <div className="flex items-center bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
              <button
                type="button"
                onClick={() => setActiveTab('catalog')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  activeTab === 'catalog'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Skill Catalog
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('sandbox')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  activeTab === 'sandbox'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Interactive Test Sandbox
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Close skills manager"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'catalog' ? (
            <>
              {/* Presets Header */}
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Quick Domain Presets:
                  </span>
                  <span className="text-xs text-slate-400">
                    Client-isolated settings are saved automatically.
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(Object.keys(SKILL_PRESETS) as SkillPresetType[]).map((key) => {
                    const preset = SKILL_PRESETS[key];
                    const isFullyActive = preset.skillIds.every((id) => activeSkills.includes(id));
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setSkillPreset(key)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all text-left ${
                          isFullyActive
                            ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40 shadow-sm'
                            : 'bg-slate-800/60 text-slate-400 border-slate-700 hover:text-slate-200 hover:bg-slate-800'
                        }`}
                        title={preset.description}
                      >
                        {preset.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Execution Status Banner (if document has been formatted) */}
              {executedSkills.length > 0 && (
                <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-emerald-400 font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    Last Processed Document: {executedSkills.length} skills executed
                    {skippedSkills.length > 0 && (
                      <span className="text-slate-400">({skippedSkills.length} disabled/skipped)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {executedSkills.map((id) => (
                      <span
                        key={id}
                        className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px]"
                      >
                        {id}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Category Filter Pills */}
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <span className="text-xs text-slate-400 mr-2">Filter Category:</span>
                {['all', 'stem', 'academic', 'formatting', 'editorial'].map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2.5 py-1 rounded-full text-xs capitalize transition-colors ${
                      selectedCategory === cat
                        ? 'bg-slate-200 text-slate-900 font-medium'
                        : 'text-slate-400 hover:text-slate-200 bg-slate-800/60'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Skills Grid */}
              {loading ? (
                <div className="py-16 text-center text-slate-400 text-sm animate-pulse">
                  Loading registered skills catalog...
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {filteredSkills.map((skill) => {
                    const isEnabled = activeSkills.includes(skill.id);
                    const wasExecuted = executedSkills.includes(skill.id);

                    return (
                      <div
                        key={skill.id}
                        className={`p-4 rounded-xl border transition-all ${
                          isEnabled
                            ? 'bg-slate-800/70 border-slate-700/80 shadow-md'
                            : 'bg-slate-900/60 border-slate-800 opacity-60'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="text-sm font-semibold text-white">{skill.name}</h3>
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">
                                v{skill.version}
                              </span>
                              <span
                                className={`text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded border ${getCategoryColor(
                                  skill.category
                                )}`}
                              >
                                {skill.category}
                              </span>
                              {wasExecuted && (
                                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                  Ran in Pipeline
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 leading-relaxed">{skill.description}</p>
                          </div>

                          {/* Toggle Switch */}
                          <button
                            type="button"
                            role="switch"
                            aria-checked={isEnabled}
                            onClick={() => toggleSkill(skill.id, !isEnabled)}
                            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                              isEnabled ? 'bg-indigo-600' : 'bg-slate-700'
                            }`}
                          >
                            <span
                              aria-hidden="true"
                              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                                isEnabled ? 'translate-x-5' : 'translate-x-0'
                              }`}
                            />
                          </button>
                        </div>

                        <div className="mt-3 pt-2.5 border-t border-slate-700/50 flex items-center justify-between text-[11px] text-slate-500">
                          <span>Priority Order: #{skill.priority}</span>
                          <button
                            type="button"
                            onClick={() => {
                              setTestSkillId(skill.id);
                              setActiveTab('sandbox');
                            }}
                            className="text-indigo-400 hover:text-indigo-300 font-medium"
                          >
                            Test in Sandbox →
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            /* Interactive Test Sandbox */
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-3">
                <h3 className="text-sm font-semibold text-white">Live Skill Execution Sandbox</h3>
                <p className="text-xs text-slate-400">
                  Verify how any individual skill validates and transforms document snippets in isolation.
                </p>

                <div className="flex items-center gap-3">
                  <label htmlFor="skill-select" className="text-xs text-slate-300 font-medium">Select Skill:</label>
                  <select
                    id="skill-select"
                    value={testSkillId}
                    onChange={(e) => setTestSkillId(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {skills.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} (v{s.version}) - Priority {s.priority}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Input snippet */}
              <div className="space-y-1.5">
                <label htmlFor="sandbox-input" className="text-xs font-medium text-slate-300">Input Snippet:</label>
                <textarea
                  id="sandbox-input"
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
                  placeholder="Enter sample markdown or text to test..."
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleTestSkill}
                  disabled={testLoading || !testInput.trim()}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-md transition-colors disabled:opacity-50"
                >
                  {testLoading ? 'Running Transformation...' : 'Execute Skill Transformation'}
                </button>
              </div>

              {/* Transformation Result */}
              {testResult && (
                <div className="space-y-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-emerald-400 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      Execution Succeeded ({testResult.execution_time_ms} ms)
                    </span>
                    <span className="text-slate-400">
                      Modified: {testResult.modified ? 'Yes (Transformed)' : 'No (Unchanged)'}
                    </span>
                  </div>

                  {testResult.diagnostics.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400">Diagnostics:</span>
                      <ul className="list-disc list-inside text-xs text-slate-300">
                        {testResult.diagnostics.map((d, i) => (
                          <li key={i}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="space-y-1">
                    <span className="text-[11px] font-medium text-slate-400">Transformed Output:</span>
                    <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-300 whitespace-pre-wrap overflow-x-auto">
                      {testResult.text}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 flex items-center justify-between bg-slate-900/90 text-xs text-slate-400">
          <span>
            {activeSkills.length} of {skills.length} skills will process documents in pipeline.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  );
};
