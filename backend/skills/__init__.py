"""FormatAI Modular Skills Architecture.

Exports:
- BaseSkill, SkillInfo, SkillValidationResult, SkillExecutionResult
- SkillRegistry
- SkillOrchestrator, SkillOrchestrationResult
- Individual built-in skills
"""

from backend.skills.base import (
    BaseSkill,
    SkillExecutionResult,
    SkillInfo,
    SkillValidationResult,
)
from backend.skills.registry import SkillRegistry
from backend.skills.orchestrator import (
    SkillOrchestrator,
    SkillOrchestrationResult,
)
from backend.skills.academic_formatting import AcademicFormattingSkill
from backend.skills.mathematics import MathematicsSkill
from backend.skills.statistics import StatisticsSkill
from backend.skills.chemistry import ChemistrySkill
from backend.skills.citation_references import CitationReferencesSkill
from backend.skills.tables import TablesSkill
from backend.skills.exam_questions import ExamQuestionsSkill
from backend.skills.study_notes import StudyNotesSkill
from backend.skills.markdown_cleanup import MarkdownCleanupSkill
from backend.skills.scientific_document import ScientificDocumentSkill

__all__ = [
    "BaseSkill",
    "SkillExecutionResult",
    "SkillInfo",
    "SkillValidationResult",
    "SkillRegistry",
    "SkillOrchestrator",
    "SkillOrchestrationResult",
    "AcademicFormattingSkill",
    "MathematicsSkill",
    "StatisticsSkill",
    "ChemistrySkill",
    "CitationReferencesSkill",
    "TablesSkill",
    "ExamQuestionsSkill",
    "StudyNotesSkill",
    "MarkdownCleanupSkill",
    "ScientificDocumentSkill",
]
