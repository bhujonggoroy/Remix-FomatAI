import React from 'react';
import { StylePresetName } from '../types/document.ts';
import { Download, FileText, Sparkles, FileSearch, Loader2 } from 'lucide-react';

interface ExportControlsProps {
  onAnalyze: () => void;
  onFormat: () => void;
  onExportDocx: () => void;
  onExportPdf: () => void;
  preset: StylePresetName;
  filename: string;
  isProcessing: boolean;
  isExporting: boolean;
  hasContent: boolean;
}

export const ExportControls: React.FC<ExportControlsProps> = ({
  onAnalyze,
  onFormat,
  onExportDocx,
  onExportPdf,
  preset,
  filename,
  isProcessing,
  isExporting,
  hasContent,
}) => {
  const isActionDisabled = !hasContent || isProcessing || isExporting;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <span>Pipeline Execution & Document Export</span>
          </h3>
          <p className="text-xs text-slate-400">
            Target file: <span className="font-mono text-slate-300">{filename || 'manuscript'}</span>{' '}
            · Preset: <span className="font-mono text-indigo-400">{preset.toUpperCase()}</span>
          </p>
        </div>

        {/* Quick Processing Triggers */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onAnalyze}
            disabled={isActionDisabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-medium text-slate-200 hover:bg-slate-800 hover:text-white transition disabled:opacity-40 cursor-pointer"
            title="Inspect document hierarchy and formulas without rewriting"
          >
            {isProcessing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
            ) : (
              <FileSearch className="w-3.5 h-3.5 text-indigo-400" />
            )}
            <span>Analyze</span>
          </button>

          <button
            type="button"
            onClick={onFormat}
            disabled={isActionDisabled}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-xs font-semibold text-white shadow-sm transition disabled:opacity-40 cursor-pointer"
            title="Clean noise, fix hierarchy, and format document model"
          >
            {isProcessing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>Clean & Format</span>
          </button>
        </div>
      </div>

      {/* Main Export Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
        {/* Export Word (.docx) */}
        <button
          type="button"
          onClick={onExportDocx}
          disabled={isActionDisabled}
          className="group relative flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/60 hover:bg-slate-800/60 transition text-left cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-900/30 border border-blue-700/40 flex items-center justify-center text-blue-400 group-hover:scale-105 transition-transform">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-100 flex items-center gap-2">
                <span>Microsoft Word (.docx)</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-950 text-blue-300 border border-blue-800/60">
                  OpenXML
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Native Word document with mathematical equations & styling
              </p>
            </div>
          </div>
          <div className="p-2 rounded-lg bg-slate-900 text-slate-300 group-hover:bg-indigo-600 group-hover:text-white transition">
            <Download className="w-4 h-4" />
          </div>
        </button>

        {/* Export Adobe (.pdf) */}
        <button
          type="button"
          onClick={onExportPdf}
          disabled={isActionDisabled}
          className="group relative flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-rose-500/60 hover:bg-slate-800/60 transition text-left cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-rose-900/30 border border-rose-700/40 flex items-center justify-center text-rose-400 group-hover:scale-105 transition-transform">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-bold text-slate-100 flex items-center gap-2">
                <span>Adobe PDF (.pdf)</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 border border-rose-800/60">
                  ReportLab
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Publication-grade vector PDF with headers, footers & pagination
              </p>
            </div>
          </div>
          <div className="p-2 rounded-lg bg-slate-900 text-slate-300 group-hover:bg-rose-600 group-hover:text-white transition">
            <Download className="w-4 h-4" />
          </div>
        </button>
      </div>
    </div>
  );
};
