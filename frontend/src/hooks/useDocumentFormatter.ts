import { useState, useCallback, useEffect } from 'react';
import {
  DocumentAnalysis,
  DocumentProcessingOptions,
  DocumentProcessResponse,
  DocumentStructure,
  StylePresetName,
  WorkflowProgress,
} from '../types/document.ts';
import { DEFAULT_PROCESSING_OPTIONS, DocumentService } from '../services/documentService.ts';
import { ACADEMIC_SAMPLES } from '../utils/samples.ts';
import { useUserSettings } from './useUserSettings.ts';

export interface UseDocumentFormatterResult {
  // Content & Configuration
  rawText: string;
  setRawText: (text: string) => void;
  options: DocumentProcessingOptions;
  setOptions: (opts: DocumentProcessingOptions) => void;
  preset: StylePresetName;
  setPreset: (preset: StylePresetName) => void;
  filename: string;
  setFilename: (name: string) => void;

  // Pipeline Results
  analysis: DocumentAnalysis | null;
  structuredDoc: DocumentStructure | null;
  lastResponse: DocumentProcessResponse | null;
  executedSkills: string[];
  skippedSkills: string[];

  // Workflow State & Indicators
  workflow: WorkflowProgress;
  isProcessing: boolean;
  isExporting: boolean;
  lastExportedFile: { filename: string; format: 'docx' | 'pdf'; sizeBytes: number } | null;
  error: string | null;
  clearError: () => void;

  // Workflow Actions
  handleAnalyzeOnly: () => Promise<void>;
  handleFullPipeline: () => Promise<void>;
  handleExportDocx: () => Promise<void>;
  handleExportPdf: () => Promise<void>;
  loadSample: (sampleId: string) => void;
  resetAll: () => void;
}

export function useDocumentFormatter(): UseDocumentFormatterResult {
  const { profile, activeSkills, updateFormattingPreferences } = useUserSettings();

  const [rawText, setRawText] = useState<string>(ACADEMIC_SAMPLES[0].rawText);
  const [options, setInternalOptions] = useState<DocumentProcessingOptions>(
    profile?.formatting?.options || DEFAULT_PROCESSING_OPTIONS
  );
  const [preset, setInternalPreset] = useState<StylePresetName>(
    profile?.formatting?.preset || 'research_paper'
  );
  const [filename, setInternalFilename] = useState<string>(
    profile?.formatting?.customFilename || 'manuscript_formatted'
  );

  const effectiveOptions: DocumentProcessingOptions = {
    ...options,
    enabled_skills: activeSkills,
  };

  // Sync state when active isolated profile changes
  useEffect(() => {
    if (profile?.formatting) {
      setInternalOptions(profile.formatting.options);
      setInternalPreset(profile.formatting.preset);
      setInternalFilename(profile.formatting.customFilename);
    }
  }, [profile?.id]);

  const setOptions = useCallback(
    (opts: DocumentProcessingOptions) => {
      setInternalOptions(opts);
      updateFormattingPreferences({ options: opts });
    },
    [updateFormattingPreferences]
  );

  const setPreset = useCallback(
    (nextPreset: StylePresetName) => {
      setInternalPreset(nextPreset);
      updateFormattingPreferences({ preset: nextPreset });
    },
    [updateFormattingPreferences]
  );

  const setFilename = useCallback(
    (name: string) => {
      setInternalFilename(name);
      updateFormattingPreferences({ customFilename: name });
    },
    [updateFormattingPreferences]
  );

  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [structuredDoc, setStructuredDoc] = useState<DocumentStructure | null>(null);
  const [lastResponse, setLastResponse] = useState<DocumentProcessResponse | null>(null);

  const [workflow, setWorkflow] = useState<WorkflowProgress>({
    stage: 'idle',
    label: 'Ready',
    detail: 'Paste content or load an academic sample to begin.',
    progressPercent: 0,
  });

  const [error, setError] = useState<string | null>(null);
  const [lastExportedFile, setLastExportedFile] = useState<{
    filename: string;
    format: 'docx' | 'pdf';
    sizeBytes: number;
  } | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const loadSample = useCallback((sampleId: string) => {
    const found = ACADEMIC_SAMPLES.find((s) => s.id === sampleId);
    if (found) {
      setRawText(found.rawText);
      setPreset(found.preset);
      setFilename(found.id);
      setAnalysis(null);
      setStructuredDoc(null);
      setLastResponse(null);
      setLastExportedFile(null);
      setError(null);
      setWorkflow({
        stage: 'idle',
        label: 'Sample Loaded',
        detail: `Loaded "${found.title}". Click "Analyze" or "Format Document" to run pipeline.`,
        progressPercent: 0,
      });
    }
  }, []);

  const resetAll = useCallback(() => {
    setRawText('');
    setAnalysis(null);
    setStructuredDoc(null);
    setLastResponse(null);
    setLastExportedFile(null);
    setError(null);
    setWorkflow({
      stage: 'idle',
      label: 'Reset',
      detail: 'Editor cleared. Ready for new input.',
      progressPercent: 0,
    });
  }, []);

  /**
   * Runs Step 1: Content Analysis without transformation.
   */
  const handleAnalyzeOnly = useCallback(async () => {
    if (!rawText.trim()) {
      setError('Please provide academic text to analyze.');
      return;
    }

    setError(null);
    setWorkflow({
      stage: 'analyzing',
      label: 'Analyzing Content',
      detail: 'Inspecting document hierarchy, formulas, citations, and quality score...',
      progressPercent: 40,
      startedAt: Date.now(),
    });

    try {
      const result = await DocumentService.analyze(rawText, effectiveOptions);
      setAnalysis(result);
      setWorkflow({
        stage: 'completed',
        label: 'Analysis Complete',
        detail: `Structure Score: ${result.structure_quality_score}/100 with ${result.hierarchy_issues.length} hierarchy issues noted.`,
        progressPercent: 100,
        completedAt: Date.now(),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Analysis failed';
      setError(msg);
      setWorkflow({
        stage: 'failed',
        label: 'Analysis Failed',
        detail: msg,
        progressPercent: 100,
        error: msg,
      });
    }
  }, [rawText, effectiveOptions]);

  /**
   * Executes the full pipeline:
   * Paste content → Analyze → Clean → Format → Preview
   */
  const handleFullPipeline = useCallback(async () => {
    if (!rawText.trim()) {
      setError('Please provide academic text to format.');
      return;
    }

    setError(null);
    setLastExportedFile(null);

    // Stage 1: Analyze & Clean
    setWorkflow({
      stage: 'analyzing',
      label: 'Analyzing Content',
      detail: 'Evaluating structure, formulas, and prose standards...',
      progressPercent: 25,
      startedAt: Date.now(),
    });

    try {
      // Step: Cleaning & Formatting via backend service
      setWorkflow({
        stage: 'cleaning',
        label: 'Cleaning Content & Fixing Hierarchy',
        detail: 'Removing noise, normalizing mathematical notation, and structuring elements...',
        progressPercent: 60,
      });

      const response = await DocumentService.process(rawText, effectiveOptions);

      setWorkflow({
        stage: 'formatting',
        label: 'Applying Style Preset Rules',
        detail: `Standardizing typography for preset "${preset}"...`,
        progressPercent: 85,
      });

      setLastResponse(response);
      setAnalysis(response.analysis);
      setStructuredDoc(response.document);

      setWorkflow({
        stage: 'previewing',
        label: 'Ready for Preview & Export',
        detail: `Successfully processed ${response.document.stats.word_count} words across ${response.document.elements.length} structural elements.`,
        progressPercent: 100,
        completedAt: Date.now(),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Document formatting failed';
      setError(msg);
      setWorkflow({
        stage: 'failed',
        label: 'Processing Failed',
        detail: msg,
        progressPercent: 100,
        error: msg,
      });
    }
  }, [rawText, effectiveOptions, preset]);

  /**
   * Generates and triggers download of .docx
   */
  const handleExportDocx = useCallback(async () => {
    if (!rawText.trim() && !structuredDoc) {
      setError('Please provide text or format the document before exporting.');
      return;
    }

    setError(null);
    setWorkflow({
      stage: 'exporting',
      label: 'Exporting DOCX',
      detail: `Compiling OpenXML Word document with "${preset}" preset...`,
      progressPercent: 90,
      startedAt: Date.now(),
    });

    try {
      const result = await DocumentService.downloadDocx({
        document: structuredDoc,
        rawText: structuredDoc ? null : rawText,
        preset,
        customFilename: filename,
        options: effectiveOptions,
      });

      setLastExportedFile({
        filename: result.filename,
        format: 'docx',
        sizeBytes: result.sizeBytes,
      });

      setWorkflow({
        stage: 'completed',
        label: 'DOCX Downloaded',
        detail: `Exported ${result.filename} (${(result.sizeBytes / 1024).toFixed(1)} KB) successfully.`,
        progressPercent: 100,
        completedAt: Date.now(),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'DOCX export failed';
      setError(msg);
      setWorkflow({
        stage: 'failed',
        label: 'DOCX Export Failed',
        detail: msg,
        progressPercent: 100,
        error: msg,
      });
    }
  }, [rawText, structuredDoc, preset, filename, effectiveOptions]);

  /**
   * Generates and triggers download of .pdf
   */
  const handleExportPdf = useCallback(async () => {
    if (!rawText.trim() && !structuredDoc) {
      setError('Please provide text or format the document before exporting.');
      return;
    }

    setError(null);
    setWorkflow({
      stage: 'exporting',
      label: 'Exporting PDF',
      detail: `Compiling publication-grade PDF via ReportLab with "${preset}" preset...`,
      progressPercent: 90,
      startedAt: Date.now(),
    });

    try {
      const result = await DocumentService.downloadPdf({
        document: structuredDoc,
        rawText: structuredDoc ? null : rawText,
        preset,
        customFilename: filename,
        options: effectiveOptions,
      });

      setLastExportedFile({
        filename: result.filename,
        format: 'pdf',
        sizeBytes: result.sizeBytes,
      });

      setWorkflow({
        stage: 'completed',
        label: 'PDF Downloaded',
        detail: `Exported ${result.filename} (${(result.sizeBytes / 1024).toFixed(1)} KB) successfully.`,
        progressPercent: 100,
        completedAt: Date.now(),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'PDF export failed';
      setError(msg);
      setWorkflow({
        stage: 'failed',
        label: 'PDF Export Failed',
        detail: msg,
        progressPercent: 100,
        error: msg,
      });
    }
  }, [rawText, structuredDoc, preset, filename, effectiveOptions]);

  const isProcessing =
    workflow.stage === 'analyzing' ||
    workflow.stage === 'cleaning' ||
    workflow.stage === 'formatting';

  const isExporting = workflow.stage === 'exporting';

  return {
    rawText,
    setRawText,
    options,
    setOptions,
    preset,
    setPreset,
    filename,
    setFilename,

    analysis,
    structuredDoc,
    lastResponse,
    executedSkills: lastResponse?.executed_skills || [],
    skippedSkills: lastResponse?.skipped_skills || [],

    workflow,
    isProcessing,
    isExporting,
    lastExportedFile,
    error,
    clearError,

    handleAnalyzeOnly,
    handleFullPipeline,
    handleExportDocx,
    handleExportPdf,
    loadSample,
    resetAll,
  };
}
