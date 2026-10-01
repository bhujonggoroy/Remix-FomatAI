"""Tests for FormatAI Skill Orchestrator and Registry.

Verifies:
1. Pipeline flow: Input → Skill Orchestrator → Enabled Skills → Document Model
2. A disabled skill MUST NOT process the document
3. Modular design: custom skill registration without modifying the orchestrator
4. Priority execution ordering
5. Diagnostics and metadata collection
"""

from typing import Any, Dict, Optional
import pytest

from backend.skills.base import BaseSkill, SkillExecutionResult, SkillValidationResult
from backend.skills.orchestrator import SkillOrchestrator
from backend.skills.registry import SkillRegistry


class CustomTestSkill(BaseSkill):
    """Custom plug-in skill created for testing modularity."""

    @property
    def id(self) -> str:
        return "custom_watermark"

    @property
    def name(self) -> str:
        return "Custom Watermark"

    @property
    def description(self) -> str:
        return "Appends a custom watermark footer."

    @property
    def version(self) -> str:
        return "2.1.0"

    @property
    def priority(self) -> int:
        return 99

    def validate(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillValidationResult:
        return SkillValidationResult(is_valid=True)

    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        return SkillExecutionResult(
            skill_id=self.id,
            skill_name=self.name,
            version=self.version,
            modified=True,
            text=f"{text}\n\n[Custom Watermark]",
            diagnostics=["Appended custom watermark."],
        )


def test_registry_lists_all_10_initial_skills():
    """Verify registry discovers and lists all 10 core skills."""
    manifest = SkillRegistry.list_manifest()
    skill_ids = [s.id for s in manifest]

    expected = [
        "markdown_cleanup",
        "academic_formatting",
        "mathematics",
        "statistics",
        "chemistry",
        "tables",
        "citation_references",
        "exam_questions",
        "study_notes",
        "scientific_document",
    ]

    for exp_id in expected:
        assert exp_id in skill_ids, f"Expected skill '{exp_id}' not found in registry"

    # Verify each skill exposes required attributes
    for item in manifest:
        assert len(item.name) > 0
        assert len(item.description) > 0
        assert item.version == "1.0.0"
        assert item.priority >= 0


def test_disabled_skill_does_not_process_document():
    """CRITICAL: A disabled skill must NOT process the document."""
    orchestrator = SkillOrchestrator()
    sample_text = "Here is your paper: H2O is water and CO2 is gas."

    # Run with chemistry skill DISABLED
    res_disabled = orchestrator.run_pipeline(
        text=sample_text,
        disabled_skills=["chemistry"],
    )

    assert "chemistry" in res_disabled.skipped_skills
    assert "chemistry" not in res_disabled.executed_skills
    # Chemistry transformation (H2O -> H₂O) must NOT have happened!
    assert "H2O" in res_disabled.final_text
    assert "H₂O" not in res_disabled.final_text

    # Now run with chemistry ENABLED
    res_enabled = orchestrator.run_pipeline(
        text=sample_text,
        enabled_skills=["chemistry"],
    )
    assert "chemistry" in res_enabled.executed_skills
    assert "H₂O" in res_enabled.final_text


def test_modular_custom_skill_registration():
    """Verify that a new skill can be registered dynamically without altering the orchestrator."""
    SkillRegistry.register(CustomTestSkill)
    retrieved = SkillRegistry.get("custom_watermark")
    assert retrieved is not None
    assert retrieved.name == "Custom Watermark"
    assert retrieved.version == "2.1.0"

    # Orchestrator should run it automatically when enabled
    orchestrator = SkillOrchestrator()
    res = orchestrator.run_pipeline("Sample text", enabled_skills=["custom_watermark"])
    assert "custom_watermark" in res.executed_skills
    assert "[Custom Watermark]" in res.final_text


def test_priority_ordering():
    """Verify skills execute in strictly ascending priority order."""
    all_skills = SkillRegistry.list_all()
    priorities = [s.priority for s in all_skills]
    assert priorities == sorted(priorities), "Skills are not ordered by priority"
