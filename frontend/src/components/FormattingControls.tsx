import React from 'react';
import {
  DocumentProcessingOptions,
  StylePresetName,
} from '../types/document.ts';
import { STYLE_PRESETS } from '../services/documentService.ts';
import { Sliders, CheckSquare, Square, BookOpen, Layers, Sparkles } from 'lucide-react';

interface FormattingControlsProps {
  preset: StylePresetName;
  onSelectPreset: (preset: StylePresetName) => void;
  options: DocumentProcessingOptions;
  onChangeOptions: (opts: DocumentProcessingOptions) => void;
  filename: string;
  onChangeFilename: (name: string) => void;
  disabled?: boolean;
  activeSkillsCount?: number;
  onOpenSkillsManager?: () => void;
}

const STYLES_LIST = ['APA', 'IEEE', 'Harvard', 'MLA', 'Chicago'];

export const FormattingControls: React.FC<FormattingControlsProps> = ({
  preset,
  onSelectPreset,
  options,
  onChangeOptions,
  filename,
  onChangeFilename,
  disabled = false,
  activeSkillsCount,
  onOpenSkillsManager,
}) => {
  const currentPresetDetails = STYLE_PRESETS.find((p) => p.id === preset) || STYLE_PRESETS[0];

  const toggleOption = (key: keyof DocumentProcessingOptions) => {
    if (disabled) return;
    onChangeOptions({
      ...options,
      [key]: !options[key],
    });
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-white">Formatting Controls</h3>
        </div>
        <div className="flex items-center gap-2">
          {onOpenSkillsManager && (
            <button
              type="button"
              onClick={onOpenSkillsManager}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition-colors"
              title="Configure modular document processing skills"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Skills {activeSkillsCount !== undefined ? `(${activeSkillsCount} Active)` : ''}</span>
            </button>
          )}
          <span className="text-xs text-slate-400 font-mono hidden sm:inline">Preset & Rules</span>
        </div>
      </div>

      {/* Preset Cards Selection */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
          Academic Style Preset
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
          {STYLE_PRESETS.map((p) => {
            const isSelected = p.id === preset;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => onSelectPreset(p.id)}
                disabled={disabled}
                className={`p-3 rounded-lg text-left transition border cursor-pointer ${
                  isSelected
                    ? 'bg-indigo-950/70 border-indigo-500 text-white shadow-sm ring-1 ring-indigo-500/40'
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:border-slate-700'
                } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="text-xs font-bold truncate">{p.name}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                      isSelected
                        ? 'bg-indigo-700/80 text-indigo-100'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {p.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-snug">
                  {p.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Preset Typography Snapshot */}
      <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800/70 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-y-2">
        <div className="flex items-center gap-2">
          <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-300 font-medium">Font Family:</span>
          <span className="font-mono text-slate-200">{currentPresetDetails.font}</span>
        </div>
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-300 font-medium">Line Spacing:</span>
          <span className="font-mono text-slate-200">{currentPresetDetails.spacing}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-300 font-medium">Margins:</span>
          <span className="font-mono text-slate-200">1.0 in (Standard Letter)</span>
        </div>
      </div>

      {/* Rules Toggles & Citation Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
        {/* Left Column: Pipeline Switches */}
        <div className="space-y-2.5">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
            Cleanup & Normalization Rules
          </label>

          <button
            type="button"
            onClick={() => toggleOption('enable_content_cleanup')}
            disabled={disabled}
            className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-950/40 border border-slate-800 hover:bg-slate-800/50 text-left transition cursor-pointer"
          >
            <div className="pr-2">
              <div className="text-xs font-medium text-slate-200">Remove AI Noise & Prefixes</div>
              <div className="text-[11px] text-slate-400">
                Strips "Here is the paper", conversational preamble, and orphan asterisks
              </div>
            </div>
            {options.enable_content_cleanup ? (
              <CheckSquare className="w-4 h-4 text-indigo-400 shrink-0" />
            ) : (
              <Square className="w-4 h-4 text-slate-600 shrink-0" />
            )}
          </button>

          <button
            type="button"
            onClick={() => toggleOption('enable_formatting_cleanup')}
            disabled={disabled}
            className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-950/40 border border-slate-800 hover:bg-slate-800/50 text-left transition cursor-pointer"
          >
            <div className="pr-2">
              <div className="text-xs font-medium text-slate-200">Normalize Heading Hierarchy</div>
              <div className="text-[11px] text-slate-400">
                Ensures single H1 document root and prevents heading level gaps (e.g. H1 → H3)
              </div>
            </div>
            {options.enable_formatting_cleanup ? (
              <CheckSquare className="w-4 h-4 text-indigo-400 shrink-0" />
            ) : (
              <Square className="w-4 h-4 text-slate-600 shrink-0" />
            )}
          </button>

          <button
            type="button"
            onClick={() => toggleOption('smart_typography')}
            disabled={disabled}
            className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-950/40 border border-slate-800 hover:bg-slate-800/50 text-left transition cursor-pointer"
          >
            <div className="pr-2">
              <div className="text-xs font-medium text-slate-200">Smart Typography</div>
              <div className="text-[11px] text-slate-400">
                Transforms straight quotes to curly quotes, dashes to em-dashes, ellipses
              </div>
            </div>
            {options.smart_typography ? (
              <CheckSquare className="w-4 h-4 text-indigo-400 shrink-0" />
            ) : (
              <Square className="w-4 h-4 text-slate-600 shrink-0" />
            )}
          </button>
        </div>

        {/* Right Column: Citation Profile & Export Filename */}
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
              Citation Standard Profile
            </label>
            <div className="grid grid-cols-5 gap-1.5">
              {STYLES_LIST.map((style) => {
                const isSelected = options.target_style === style;
                return (
                  <button
                    key={style}
                    type="button"
                    onClick={() =>
                      onChangeOptions({
                        ...options,
                        target_style: style,
                      })
                    }
                    disabled={disabled}
                    className={`py-1.5 px-2 text-xs font-medium rounded-md text-center transition border cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-600 border-indigo-500 text-white font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                    }`}
                  >
                    {style}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Select bibliography formatting convention applied to recognized reference blocks.
            </p>
          </div>

          <div>
            <label
              htmlFor="document-filename"
              className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5"
            >
              Export Filename
            </label>
            <div className="flex items-center rounded-lg bg-slate-950 border border-slate-800 overflow-hidden focus-within:border-indigo-500">
              <input
                id="document-filename"
                type="text"
                value={filename}
                onChange={(e) => onChangeFilename(e.target.value)}
                disabled={disabled}
                placeholder="manuscript_formatted"
                className="w-full bg-transparent px-3 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none"
              />
              <span className="px-2.5 py-2 text-xs font-mono text-slate-500 bg-slate-900 border-l border-slate-800">
                .docx / .pdf
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
