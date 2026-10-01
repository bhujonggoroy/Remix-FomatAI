import { apiClient } from './api.ts';
import {
  DocumentAnalysis,
  DocumentProcessingOptions,
  DocumentProcessResponse,
  DocumentStructure,
  StylePresetName,
  StylePresetOption,
} from '../types/document.ts';
import { formatFilename, triggerBlobDownload } from '../utils/download.ts';

export const STYLE_PRESETS: StylePresetOption[] = [
  {
    id: 'academic',
    name: 'Standard Academic',
    description: 'APA style, double-spaced, 0.5-inch paragraph indent, Times New Roman, 1-inch margins.',
    font: 'Times New Roman',
    spacing: 'Double Spaced (2.0)',
    badge: 'APA Standard',
  },
  {
    id: 'research_paper',
    name: 'IEEE / ACM Research Paper',
    description: 'Formal serif, compact 1.15 line spacing, numbered hierarchical sections, clean header borders.',
    font: 'Times New Roman',
    spacing: 'Compact (1.15)',
    badge: 'IEEE / ACM',
  },
  {
    id: 'exam',
    name: 'Examination Paper',
    description: 'Structured question blocks, mark indicators, high-contrast sans headings, derivation space.',
    font: 'Calibri / Arial',
    spacing: '1.25 with Question Gaps',
    badge: 'Assessment',
  },
  {
    id: 'study_notes',
    name: 'Study Notes & Summary',
    description: 'Scannable typography, bullet item accents, clear table cards, and highlighted definition blocks.',
    font: 'Plus Jakarta Sans',
    spacing: 'Relaxed (1.3)',
    badge: 'Revision Guide',
  },
  {
    id: 'textbook',
    name: 'Textbook / Reference Guide',
    description: 'Multi-chapter hierarchy, formal math derivations, shaded table headers, and citation indexes.',
    font: 'Georgia / Times',
    spacing: '1.2 with Paragraph Spacing',
    badge: 'Monograph',
  },
];

export const DEFAULT_PROCESSING_OPTIONS: DocumentProcessingOptions = {
  enable_content_cleanup: true,
  enable_formatting_cleanup: true,
  target_style: 'APA',
  smart_typography: true,
};

export class DocumentService {
  /**
   * Performs read-only structural analysis of raw content.
   */
  static async analyze(rawText: string, options = DEFAULT_PROCESSING_OPTIONS): Promise<DocumentAnalysis> {
    return apiClient.analyzeDocument({
      raw_text: rawText,
      options,
    });
  }

  /**
   * Executes the full document cleaning and formatting pipeline.
   */
  static async process(rawText: string, options = DEFAULT_PROCESSING_OPTIONS): Promise<DocumentProcessResponse> {
    return apiClient.processDocument({
      raw_text: rawText,
      options,
    });
  }

  /**
   * Generates and downloads a .docx file.
   */
  static async downloadDocx(params: {
    document?: DocumentStructure | null;
    rawText?: string | null;
    preset: StylePresetName;
    customFilename?: string | null;
    options?: DocumentProcessingOptions;
  }): Promise<{ filename: string; sizeBytes: number }> {
    const defaultName = params.customFilename || params.document?.title || 'academic_document';
    const targetFilename = formatFilename(defaultName, 'docx');

    const blob = await apiClient.exportDocx({
      document: params.document,
      raw_text: params.rawText,
      preset: params.preset,
      filename: targetFilename,
      options: params.options,
    });

    triggerBlobDownload(blob, targetFilename);

    return {
      filename: targetFilename,
      sizeBytes: blob.size,
    };
  }

  /**
   * Generates and downloads an Adobe PDF file.
   */
  static async downloadPdf(params: {
    document?: DocumentStructure | null;
    rawText?: string | null;
    preset: StylePresetName;
    customFilename?: string | null;
    options?: DocumentProcessingOptions;
  }): Promise<{ filename: string; sizeBytes: number }> {
    const defaultName = params.customFilename || params.document?.title || 'academic_document';
    const targetFilename = formatFilename(defaultName, 'pdf');

    const blob = await apiClient.exportPdf({
      document: params.document,
      raw_text: params.rawText,
      preset: params.preset,
      filename: targetFilename,
      options: params.options,
    });

    triggerBlobDownload(blob, targetFilename);

    return {
      filename: targetFilename,
      sizeBytes: blob.size,
    };
  }
}
