"""Skill Registry for FormatAI modular Document-Processing Skills.

Manages registration, lookup, metadata listing, and dynamic skill extension.
"""

from typing import Dict, List, Optional, Type
from backend.skills.base import BaseSkill, SkillInfo
from backend.skills.markdown_cleanup import MarkdownCleanupSkill
from backend.skills.academic_formatting import AcademicFormattingSkill
from backend.skills.mathematics import MathematicsSkill
from backend.skills.statistics import StatisticsSkill
from backend.skills.chemistry import ChemistrySkill
from backend.skills.tables import TablesSkill
from backend.skills.citation_references import CitationReferencesSkill
from backend.skills.exam_questions import ExamQuestionsSkill
from backend.skills.study_notes import StudyNotesSkill
from backend.skills.scientific_document import ScientificDocumentSkill


class SkillRegistry:
    """Central registry for discovering and instantiating document-processing skills."""

    _skills: Dict[str, Type[BaseSkill]] = {}
    _instances: Dict[str, BaseSkill] = {}

    @classmethod
    def register(cls, skill_cls: Type[BaseSkill]) -> None:
        """Registers a skill class in the registry."""
        inst = skill_cls()
        cls._skills[inst.id] = skill_cls
        cls._instances[inst.id] = inst

    @classmethod
    def get(cls, skill_id: str) -> Optional[BaseSkill]:
        """Retrieves a cached skill instance by its unique identifier."""
        norm_id = skill_id.strip().lower()
        if norm_id in cls._instances:
            return cls._instances[norm_id]
        if norm_id in cls._skills:
            inst = cls._skills[norm_id]()
            cls._instances[norm_id] = inst
            return inst
        return None

    @classmethod
    def list_all(cls) -> List[BaseSkill]:
        """Returns all registered skills sorted by execution priority."""
        cls._ensure_initialized()
        return sorted(cls._instances.values(), key=lambda s: s.priority)

    @classmethod
    def list_manifest(cls) -> List[SkillInfo]:
        """Returns public metadata info for all registered skills."""
        cls._ensure_initialized()
        return [skill.get_info() for skill in cls.list_all()]

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Bootstraps default skills if registry is empty."""
        if not cls._skills:
            default_classes: List[Type[BaseSkill]] = [
                MarkdownCleanupSkill,
                AcademicFormattingSkill,
                MathematicsSkill,
                StatisticsSkill,
                ChemistrySkill,
                TablesSkill,
                CitationReferencesSkill,
                ExamQuestionsSkill,
                StudyNotesSkill,
                ScientificDocumentSkill,
            ]
            for s_cls in default_classes:
                cls.register(s_cls)


# Bootstrap on module import
SkillRegistry._ensure_initialized()
