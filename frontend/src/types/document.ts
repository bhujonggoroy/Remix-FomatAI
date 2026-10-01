export type DocumentElementType =
  | 'title'
  | 'heading'
  | 'paragraph'
  | 'ordered_list'
  | 'unordered_list'
  | 'table'
  | 'blockquote'
  | 'code_block'
  | 'math_block'
  | 'citation'
  | 'reference_item'
  | 'reference_list'
  | 'abstract'
  | 'metadata';

export type EntityType =
  | 'inline_math'
  | 'display_math'
  | 'scientific_notation'
  | 'chemical_formula'
  | 'citation_reference'
  | 'bold'
  | 'italic'
  | 'code_inline';

export interface InlineEntity {
  entity_type: EntityType;
  raw_text: string;
  normalized_text: string;
  start: number;
  end: number;
  metadata?: Record<string, unknown>;
}

export type TableColumnAlign = 'left' | 'center' | 'right';

export interface TableData {
  headers: string[];
  rows: string[][];
  alignments?: TableColumnAlign[];
  caption?: string | null;
}

export interface DocumentElement {
  id: string;
  type: DocumentElementType;
  content: string;
  raw_content: string;
  level?: number | null;
  items?: string[] | null;
  table_data?: TableData | null;
  language?: string | null;
  math_syntax?: string | null;
  entities: InlineEntity[];
  metadata: Record<string, unknown>;
}

export interface DocumentStats {
  word_count: number;
  character_count: number;
  reading_time_minutes: number;
  paragraph_count: number;
  heading_count: number;
  table_count: number;
  math_block_count: number;
  citation_count: number;
  reference_count: number;
}

export interface DocumentAnalysis {
  detected_title?: string | null;
  has_abstract: boolean;
  has_references: boolean;
  detected_style_candidate?: string | null;
  heading_hierarchy_valid: boolean;
  hierarchy_issues: string[];
  math_density: number;
  structure_quality_score: number;
  detected_entities_summary: Record<string, number>;
  diagnostics: string[];
}

export interface DocumentStructure {
  title?: string | null;
  abstract?: string | null;
  elements: DocumentElement[];
  stats: DocumentStats;
  references: string[];
  metadata: Record<string, unknown>;
}

export type StylePresetName =
  | 'academic'
  | 'research_paper'
  | 'exam'
  | 'study_notes'
  | 'textbook';

export interface StylePresetOption {
  id: StylePresetName;
  name: string;
  description: string;
  font: string;
  spacing: string;
  badge: string;
}

export interface DocumentProcessingOptions {
  enable_content_cleanup: boolean;
  enable_formatting_cleanup: boolean;
  target_style: string;
  smart_typography: boolean;
  enabled_skills?: string[];
  disabled_skills?: string[];
}

export interface DocumentProcessRequest {
  raw_text: string;
  options?: DocumentProcessingOptions;
}

export interface DocumentProcessResponse {
  success: boolean;
  document: DocumentStructure;
  analysis: DocumentAnalysis;
  executed_skills?: string[];
  skipped_skills?: string[];
  pipeline_stages?: Record<string, unknown>;
}

export interface DocumentExportRequest {
  document?: DocumentStructure | null;
  raw_text?: string | null;
  preset: StylePresetName;
  filename?: string | null;
  options?: DocumentProcessingOptions;
}

export type WorkflowStage =
  | 'idle'
  | 'analyzing'
  | 'cleaning'
  | 'formatting'
  | 'previewing'
  | 'exporting'
  | 'completed'
  | 'failed';

export interface WorkflowProgress {
  stage: WorkflowStage;
  label: string;
  detail: string;
  progressPercent: number;
  startedAt?: number;
  completedAt?: number;
  error?: string | null;
}
