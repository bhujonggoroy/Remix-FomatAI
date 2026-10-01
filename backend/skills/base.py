"""Base contract and abstractions for FormatAI modular Document-Processing Skills.

Each Skill is an independent capability with its own name, description, version,
enabled state, processing rules, validation logic, and test coverage.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillValidationResult(BaseModel):
    """Outcome of validating a document or text against skill criteria."""
    is_valid: bool = True
    issues: List[str] = Field(default_factory=list)
    detected_features: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class SkillExecutionResult(BaseModel):
    """Outcome of executing a skill's processing rules on text."""
    skill_id: str
    skill_name: str
    version: str
    modified: bool = False
    text: str
    diagnostics: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0


class SkillInfo(BaseModel):
    """Public metadata representation of a Skill."""
    id: str
    name: str
    description: str
    version: str
    enabled_by_default: bool = True
    priority: int = 50
    category: str = "general"
    supported_formats: List[str] = Field(default_factory=lambda: ["markdown", "latex", "text"])


class BaseSkill(ABC):
    """Abstract Base Class for all document-processing skills."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique kebab-case or snake_case identifier."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of the processing capability."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the skill (e.g. '1.0.0')."""
        pass

    @property
    def enabled_by_default(self) -> bool:
        """Default enabled status if not overridden by user settings."""
        return True

    @property
    def priority(self) -> int:
        """Execution priority (lower runs earlier; default 50).
        0-29: Pre-processing & Cleanup
        30-69: Domain Semantic Processing (Math, Chemistry, Tables, etc.)
        70-100: Post-processing & Document Synthesis
        """
        return 50

    @property
    def category(self) -> str:
        """Category taxonomy: 'formatting', 'stem', 'editorial', 'academic'."""
        return "academic"

    def get_info(self) -> SkillInfo:
        """Returns standard metadata for this skill."""
        return SkillInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            version=self.version,
            enabled_by_default=self.enabled_by_default,
            priority=self.priority,
            category=self.category,
        )

    @abstractmethod
    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        """Validates whether the text contains relevant patterns or syntax issues."""
        pass

    @abstractmethod
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        """Executes transformation rules on the text."""
        pass
