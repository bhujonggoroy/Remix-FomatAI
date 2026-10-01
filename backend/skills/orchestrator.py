"""Skill Orchestrator for FormatAI.

Executes the modular document processing flow:
Input → Skill Orchestrator → Enabled Skills → Document Model → Export

Guarantees:
- A disabled skill MUST NOT process the document.
- Skills execute in strict priority order (0-100).
- Modular design: adding a new skill requires zero changes to the orchestrator.
- Comprehensive execution tracking, metrics, and diagnostics collection.
"""

import time
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from backend.core.logging import logger
from backend.skills.base import SkillExecutionResult, SkillValidationResult
from backend.skills.registry import SkillRegistry


class SkillOrchestrationResult(BaseModel):
    """Result of running input text through the enabled skills pipeline."""
    initial_text: str
    final_text: str
    is_modified: bool
    enabled_skills: List[str] = Field(default_factory=list)
    skipped_skills: List[str] = Field(default_factory=list)
    executed_skills: List[str] = Field(default_factory=list)
    skill_results: List[SkillExecutionResult] = Field(default_factory=list)
    all_diagnostics: List[str] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0


class SkillOrchestrator:
    """Orchestrates sequential execution of enabled modular document-processing skills."""

    def __init__(self, registry: Optional[SkillRegistry] = None):
        self._registry = registry or SkillRegistry

    def get_registered_skills(self) -> List[Any]:
        """Returns all registered skills in priority order."""
        return self._registry.list_all()

    def run_pipeline(
        self,
        text: str,
        enabled_skills: Optional[List[str]] = None,
        disabled_skills: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SkillOrchestrationResult:
        """Executes the pipeline: Input → Skill Orchestrator → Enabled Skills → Result.

        A disabled skill MUST NOT process the document.
        """
        start_time = time.time()
        all_skills = self._registry.list_all()
        current_text = text

        # Determine effective enabled set
        enabled_filter: Optional[Set[str]] = (
            {s.strip().lower() for s in enabled_skills} if enabled_skills is not None else None
        )
        disabled_filter: Set[str] = (
            {s.strip().lower() for s in disabled_skills} if disabled_skills is not None else set()
        )

        executed_names: List[str] = []
        skipped_names: List[str] = []
        active_skill_ids: List[str] = []
        results: List[SkillExecutionResult] = []
        all_diagnostics: List[str] = []

        logger.info(f"SkillOrchestrator starting pipeline for text ({len(text)} chars)")

        for skill in all_skills:
            # Check if skill is enabled
            if enabled_filter is not None:
                is_active = (skill.id in enabled_filter) and (skill.id not in disabled_filter)
            else:
                is_active = skill.enabled_by_default and (skill.id not in disabled_filter)

            if not is_active:
                skipped_names.append(skill.id)
                logger.debug(f"Skill '{skill.id}' is disabled; skipping processing.")
                continue

            active_skill_ids.append(skill.id)
            try:
                # Execute skill
                res = skill.process(current_text, context=context)
                results.append(res)
                executed_names.append(skill.id)

                if res.diagnostics:
                    all_diagnostics.extend(res.diagnostics)

                if res.modified:
                    current_text = res.text
                    logger.debug(f"Skill '{skill.id}' modified document text.")

            except Exception as exc:
                logger.error(f"Error executing skill '{skill.id}': {exc}", exc_info=True)
                all_diagnostics.append(f"Skill '{skill.name}' encountered an error: {exc}")

        total_duration = (time.time() - start_time) * 1000.0

        return SkillOrchestrationResult(
            initial_text=text,
            final_text=current_text,
            is_modified=current_text != text,
            enabled_skills=active_skill_ids,
            skipped_skills=skipped_names,
            executed_skills=executed_names,
            skill_results=results,
            all_diagnostics=all_diagnostics,
            total_execution_time_ms=round(total_duration, 2),
        )

    def validate_all(
        self,
        text: str,
        enabled_skills: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, SkillValidationResult]:
        """Runs validation across all requested skills."""
        all_skills = self._registry.list_all()
        enabled_filter = {s.strip().lower() for s in enabled_skills} if enabled_skills is not None else None

        validations: Dict[str, SkillValidationResult] = {}
        for skill in all_skills:
            if enabled_filter is not None and skill.id not in enabled_filter:
                continue
            validations[skill.id] = skill.validate(text, context=context)

        return validations
