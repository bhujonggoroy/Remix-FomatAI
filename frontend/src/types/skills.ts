/**
 * Modular Document-Processing Skill types and presets.
 */

export interface SkillInfo {
  id: string;
  name: string;
  description: string;
  version: string;
  enabled_by_default: boolean;
  priority: number;
  category: 'formatting' | 'stem' | 'editorial' | 'academic';
  supported_formats?: string[];
}

export interface SkillValidationResult {
  is_valid: boolean;
  issues: string[];
  detected_features: string[];
  confidence_score: number;
  metrics: Record<string, unknown>;
}

export interface SkillExecutionResult {
  skill_id: string;
  skill_name: string;
  version: string;
  modified: boolean;
  text: string;
  diagnostics: string[];
  metadata: Record<string, unknown>;
  execution_time_ms: number;
}

export interface SkillOrchestrationResult {
  initial_text: string;
  final_text: string;
  is_modified: boolean;
  enabled_skills: string[];
  skipped_skills: string[];
  executed_skills: string[];
  skill_results: SkillExecutionResult[];
  all_diagnostics: string[];
  total_execution_time_ms: number;
}

export type SkillPresetType = 'all' | 'stem' | 'humanities' | 'exam' | 'minimal';

export const SKILL_PRESETS: Record<SkillPresetType, { label: string; description: string; skillIds: string[] }> = {
  all: {
    label: 'All Skills (Comprehensive)',
    description: 'Enables all 10 document-processing capabilities.',
    skillIds: [
      'markdown_cleanup',
      'academic_formatting',
      'mathematics',
      'statistics',
      'chemistry',
      'tables',
      'citation_references',
      'exam_questions',
      'study_notes',
      'scientific_document',
    ],
  },
  stem: {
    label: 'STEM & Natural Sciences',
    description: 'Focuses on Mathematics, Statistics, Chemistry, Tables, and Scientific IMRaD.',
    skillIds: [
      'markdown_cleanup',
      'academic_formatting',
      'mathematics',
      'statistics',
      'chemistry',
      'tables',
      'scientific_document',
      'citation_references',
    ],
  },
  humanities: {
    label: 'Humanities & Social Sciences',
    description: 'Focuses on Academic Formatting, Citations/References, Tables, and Markdown Cleanup.',
    skillIds: [
      'markdown_cleanup',
      'academic_formatting',
      'citation_references',
      'tables',
      'scientific_document',
    ],
  },
  exam: {
    label: 'Exam & Educational Prep',
    description: 'Specialized for problem sets, multiple-choice options, and study summaries.',
    skillIds: [
      'markdown_cleanup',
      'exam_questions',
      'study_notes',
      'tables',
      'academic_formatting',
    ],
  },
  minimal: {
    label: 'Minimal Cleanup Only',
    description: 'Only runs essential Markdown cleanup and heading typography.',
    skillIds: ['markdown_cleanup', 'academic_formatting'],
  },
};

export const DEFAULT_SKILL_MANIFEST: SkillInfo[] = [
  {
    id: 'markdown_cleanup',
    name: 'Markdown Cleanup',
    description: 'Removes conversational AI prefixes, fixes orphan list markers, and standardizes whitespace.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 10,
    category: 'editorial',
  },
  {
    id: 'academic_formatting',
    name: 'Academic Formatting',
    description: 'Standardizes heading hierarchy (H1-H4), smart typography, and academic paragraph margins.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 20,
    category: 'formatting',
  },
  {
    id: 'mathematics',
    name: 'Mathematics',
    description: 'Normalizes LaTeX equations ($...$ and $$...$$), operator symbols, and theorem environments.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 30,
    category: 'stem',
  },
  {
    id: 'statistics',
    name: 'Statistics',
    description: 'Standardizes statistical reporting (APA-compliant p-values, *t*/*F*/*r* notation, and confidence intervals).',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 35,
    category: 'stem',
  },
  {
    id: 'chemistry',
    name: 'Chemistry',
    description: 'Normalizes chemical formulas (H₂O, CO₂), reaction arrows (→, ⇌), and ionic charges.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 40,
    category: 'stem',
  },
  {
    id: 'tables',
    name: 'Tables',
    description: 'Validates and standardizes academic Markdown tables, column alignments, and table captions.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 45,
    category: 'formatting',
  },
  {
    id: 'citation_references',
    name: 'Citation/References',
    description: 'Detects and normalizes in-text citations (APA/IEEE) and standardizes reference list sections.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 50,
    category: 'academic',
  },
  {
    id: 'exam_questions',
    name: 'Exam Questions',
    description: 'Standardizes exam questions, multiple-choice options ((A)-(D)), and point allocations.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 60,
    category: 'academic',
  },
  {
    id: 'study_notes',
    name: 'Study Notes',
    description: 'Formats key concepts, definitions into highlighted callouts, and structures study takeaways.',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 65,
    category: 'academic',
  },
  {
    id: 'scientific_document',
    name: 'Scientific Document Formatting',
    description: 'Enforces standard scientific manuscript structure (IMRaD sections, Keywords, affiliations).',
    version: '1.0.0',
    enabled_by_default: true,
    priority: 70,
    category: 'academic',
  },
];
