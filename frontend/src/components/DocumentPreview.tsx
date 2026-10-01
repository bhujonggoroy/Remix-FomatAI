import React, { useState } from 'react';
import {
  DocumentAnalysis,
  DocumentElement,
  DocumentStructure,
  StylePresetName,
} from '../types/document.ts';
import {
  FileText,
  Activity,
  Code2,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Maximize2,
  Minimize2,
} from 'lucide-react';

interface DocumentPreviewProps {
  document: DocumentStructure | null;
  analysis: DocumentAnalysis | null;
  preset: StylePresetName;
  rawInput: string;
  isProcessing: boolean;
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  document,
  analysis,
  preset,
  rawInput,
  isProcessing,
}) => {
  const [activeTab, setActiveTab] = useState<'paper' | 'structure' | 'raw'>('paper');
  const [copied, setCopied] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<'normal' | 'fit'>('normal');

  // Copy raw or cleaned text
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // Font family determination based on preset
  const getPaperFontClass = () => {
    switch (preset) {
      case 'research_paper':
      case 'academic':
      case 'textbook':
        return 'font-serif text-slate-900';
      case 'exam':
      case 'study_notes':
      default:
        return 'font-sans text-slate-900';
    }
  };

  const getLineSpacingClass = () => {
    switch (preset) {
      case 'academic':
        return 'leading-loose'; // APA double spaced
      case 'research_paper':
        return 'leading-normal text-xs'; // Compact IEEE
      case 'study_notes':
        return 'leading-relaxed text-sm';
      default:
        return 'leading-normal text-sm';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col h-full shadow-sm">
      {/* Preview Header & View Mode Switcher */}
      <div className="bg-slate-950 px-4 py-2.5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab('paper')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition cursor-pointer ${
              activeTab === 'paper'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Academic Paper</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('structure')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition cursor-pointer ${
              activeTab === 'structure'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Analysis & Structure</span>
            {analysis && (
              <span className="text-[10px] font-mono px-1 rounded bg-indigo-900 text-indigo-200 ml-0.5">
                {analysis.structure_quality_score}%
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('raw')}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition cursor-pointer ${
              activeTab === 'raw'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Cleaned Markdown</span>
          </button>
        </div>

        {/* Viewport Control Tools */}
        <div className="flex items-center gap-2">
          {isProcessing && (
            <span className="flex items-center gap-1.5 text-xs text-indigo-400 font-mono animate-pulse mr-2">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              Formatting...
            </span>
          )}
          {activeTab === 'paper' && (
            <button
              type="button"
              onClick={() => setZoomLevel(zoomLevel === 'normal' ? 'fit' : 'normal')}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition cursor-pointer"
              title={zoomLevel === 'normal' ? 'Fit to Screen' : 'Standard 100%'}
            >
              {zoomLevel === 'normal' ? (
                <Maximize2 className="w-3.5 h-3.5" />
              ) : (
                <Minimize2 className="w-3.5 h-3.5" />
              )}
            </button>
          )}

          <button
            type="button"
            onClick={() => handleCopy(rawInput)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs text-slate-300 bg-slate-900 border border-slate-800 rounded-md hover:bg-slate-800 transition cursor-pointer"
            title="Copy document text"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Main Preview Container */}
      <div className="flex-1 overflow-auto p-4 sm:p-6 bg-slate-950 flex justify-center items-start min-h-[440px]">
        {/* Tab 1: Rendered Academic Paper */}
        {activeTab === 'paper' && (
          <div
            className={`bg-white text-slate-900 rounded shadow-2xl p-8 sm:p-12 w-full transition-all border border-slate-300 ${
              zoomLevel === 'normal' ? 'max-w-[760px]' : 'max-w-[920px]'
            } ${getPaperFontClass()}`}
            style={{
              minHeight: '840px',
              boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.4)',
            }}
          >
            {/* Header Running Head Simulation */}
            <div className="border-b border-slate-200 pb-2 mb-8 flex items-center justify-between text-[11px] text-slate-500 font-sans tracking-wide uppercase">
              <span className="truncate max-w-sm">
                {document?.title || 'FormatAI Academic Manuscript'}
              </span>
              <span>Preset: {preset.toUpperCase()}</span>
            </div>

            {/* Document Title */}
            {document?.title && (
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 text-center mb-6 text-balance">
                {document.title}
              </h1>
            )}

            {/* Abstract Callout */}
            {document?.abstract && (
              <div className="my-6 px-6 py-4 bg-slate-50 border-l-4 border-indigo-600 rounded-r text-xs leading-relaxed italic text-slate-800">
                <span className="font-bold not-italic font-sans uppercase tracking-wider text-[11px] block mb-1 text-indigo-900">
                  Abstract
                </span>
                {document.abstract}
              </div>
            )}

            {/* Elements Stream */}
            <div className={`space-y-4 ${getLineSpacingClass()}`}>
              {document && document.elements.length > 0 ? (
                document.elements.map((el) => (
                  <RenderElement key={el.id} element={el} preset={preset} />
                ))
              ) : rawInput.trim() ? (
                <div className="space-y-4 text-slate-800 text-sm whitespace-pre-wrap">
                  {rawInput}
                </div>
              ) : (
                <div className="py-24 text-center text-slate-400">
                  <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p className="text-sm font-medium">No manuscript content yet</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Paste raw text in the editor or load a template above to generate a preview.
                  </p>
                </div>
              )}
            </div>

            {/* Reference Catalog */}
            {document?.references && document.references.length > 0 && (
              <div className="mt-12 pt-6 border-t border-slate-300">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 mb-4 font-sans">
                  References
                </h3>
                <ol className="space-y-2 text-xs leading-relaxed text-slate-800 list-decimal pl-5">
                  {document.references.map((ref, idx) => (
                    <li key={idx} className="pl-1">
                      {ref}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Footer Pagination Simulation */}
            <div className="border-t border-slate-200 mt-12 pt-4 flex items-center justify-between text-[11px] text-slate-400 font-sans">
              <span>FormatAI Automated Typesetting</span>
              <span className="font-mono">Page 1 of 1</span>
            </div>
          </div>
        )}

        {/* Tab 2: Structural Inspection & Diagnostics */}
        {activeTab === 'structure' && (
          <div className="w-full max-w-4xl space-y-5 text-slate-200">
            {/* Analysis Scorecard */}
            {analysis ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="text-xs text-slate-400 font-medium">Structure Quality Score</div>
                  <div className="text-2xl font-bold font-mono mt-1 text-indigo-400">
                    {analysis.structure_quality_score.toFixed(1)} / 100
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    Computed based on heading validity and element consistency
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="text-xs text-slate-400 font-medium">Mathematical Density</div>
                  <div className="text-2xl font-bold font-mono mt-1 text-emerald-400">
                    {analysis.math_density.toFixed(2)}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    Equations & formulas detected across content
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="text-xs text-slate-400 font-medium">Heading Hierarchy</div>
                  <div className="mt-1 flex items-center gap-1.5">
                    {analysis.heading_hierarchy_valid ? (
                      <div className="flex items-center gap-1 text-emerald-400 text-sm font-semibold">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Valid Hierarchy</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-amber-400 text-sm font-semibold">
                        <AlertTriangle className="w-4 h-4" />
                        <span>Hierarchy Discrepancies</span>
                      </div>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    {analysis.hierarchy_issues.length === 0
                      ? 'No orphan headings or level skips'
                      : `${analysis.hierarchy_issues.length} issue(s) detected`}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400">
                Click "Analyze" or "Format Document" to view structural diagnostics and hierarchy audit.
              </div>
            )}

            {/* Document Stats Breakdown */}
            {document?.stats && (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Element Inventory & Metrics
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono tabular-nums">
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Words</span>
                    <span className="text-white text-base font-bold">
                      {document.stats.word_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Headings</span>
                    <span className="text-white text-base font-bold">
                      {document.stats.heading_count}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Tables</span>
                    <span className="text-white text-base font-bold">
                      {document.stats.table_count}
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-800/80">
                    <span className="text-slate-500 block text-[11px]">Math Blocks</span>
                    <span className="text-white text-base font-bold">
                      {document.stats.math_block_count}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Diagnostics List */}
            {analysis?.diagnostics && analysis.diagnostics.length > 0 && (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Quality Diagnostics Log
                </h4>
                <div className="space-y-1 text-xs font-mono text-slate-300">
                  {analysis.diagnostics.map((d, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-indigo-400">▸</span>
                      <span>{d}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Cleaned Markdown View */}
        {activeTab === 'raw' && (
          <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
            {document
              ? document.elements.map((e) => e.raw_content || e.content).join('\n\n')
              : rawInput || 'No content loaded'}
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// RenderElement Sub-component
// ---------------------------------------------------------------------------

interface RenderElementProps {
  element: DocumentElement;
  preset: StylePresetName;
}

const RenderElement: React.FC<RenderElementProps> = ({ element }) => {
  switch (element.type) {
    case 'title':
      return null; // Title handled at top of paper

    case 'heading': {
      const level = element.level || 2;
      if (level === 1) {
        return (
          <h2 className="text-lg font-bold text-slate-950 mt-6 mb-2 border-b border-slate-300 pb-1 font-sans">
            {element.content}
          </h2>
        );
      } else if (level === 2) {
        return (
          <h3 className="text-base font-semibold text-slate-900 mt-5 mb-1.5 font-sans">
            {element.content}
          </h3>
        );
      }
      return (
        <h4 className="text-sm font-semibold text-slate-800 mt-4 mb-1 italic font-sans">
          {element.content}
        </h4>
      );
    }

    case 'paragraph':
      return <p className="text-slate-800 text-justify mb-3">{element.content}</p>;

    case 'table': {
      const tableData = element.table_data;
      if (!tableData) return null;
      return (
        <div className="my-5 overflow-x-auto">
          {tableData.caption && (
            <div className="text-xs font-semibold text-slate-700 italic mb-1.5">
              {tableData.caption}
            </div>
          )}
          <table className="w-full border-collapse border border-slate-300 text-xs">
            {tableData.headers && tableData.headers.length > 0 && (
              <thead>
                <tr className="bg-slate-100 border-b border-slate-300">
                  {tableData.headers.map((h, i) => (
                    <th key={i} className="p-2 border border-slate-300 text-left font-bold text-slate-900">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {tableData.rows.map((row, rIdx) => (
                <tr key={rIdx} className={rIdx % 2 === 1 ? 'bg-slate-50' : 'bg-white'}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="p-2 border border-slate-300 text-slate-800">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    case 'math_block':
      return (
        <div className="my-4 p-3 bg-slate-50 border border-slate-200 rounded text-center font-mono text-xs text-slate-900 overflow-x-auto shadow-inner">
          {element.content}
        </div>
      );

    case 'blockquote':
      return (
        <blockquote className="my-3 pl-4 border-l-2 border-slate-400 italic text-slate-700 text-sm">
          {element.content}
        </blockquote>
      );

    case 'ordered_list':
    case 'unordered_list':
      return (
        <div className="my-2 pl-5 space-y-1 text-slate-800 text-xs">
          {element.items?.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <span className="font-bold text-slate-500">
                {element.type === 'ordered_list' ? `${idx + 1}.` : '•'}
              </span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      );

    case 'code_block':
      return (
        <pre className="my-3 p-3 bg-slate-900 text-slate-200 rounded font-mono text-xs overflow-x-auto leading-relaxed">
          <code>{element.content}</code>
        </pre>
      );

    default:
      return <div className="text-xs text-slate-700">{element.content}</div>;
  }
};
