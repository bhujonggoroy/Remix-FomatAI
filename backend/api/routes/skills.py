"""Skills API routes for querying, validating, and testing modular skills."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.skills.base import SkillExecutionResult, SkillInfo, SkillValidationResult
from backend.skills.orchestrator import SkillOrchestrationResult, SkillOrchestrator
from backend.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/skills", tags=["Modular Document-Processing Skills"])


class SkillTextRequest(BaseModel):
    """Payload for executing or validating a specific skill on raw text."""
    text: str = Field(..., min_length=1, description="Raw text snippet to evaluate or transform")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional styling context")


class SkillPipelineRequest(BaseModel):
    """Payload for running text through a custom selection of enabled skills."""
    text: str = Field(..., min_length=1, description="Raw text to run through the skills pipeline")
    enabled_skills: Optional[List[str]] = Field(default=None, description="Explicit skills to run")
    disabled_skills: Optional[List[str]] = Field(default=None, description="Skills to skip")


@router.get(
    "",
    response_model=List[SkillInfo],
    summary="List all registered document-processing skills",
    description="Returns the full catalog of modular skills available in FormatAI.",
)
def list_skills() -> List[SkillInfo]:
    """Returns metadata for all registered skills ordered by execution priority."""
    return SkillRegistry.list_manifest()


@router.get(
    "/{skill_id}",
    response_model=SkillInfo,
    responses={404: {"description": "Skill not found"}},
    summary="Get single skill metadata",
)
def get_skill(skill_id: str) -> SkillInfo:
    """Returns metadata for a specific skill."""
    skill = SkillRegistry.get(skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' is not registered.",
        )
    return skill.get_info()


@router.post(
    "/{skill_id}/validate",
    response_model=SkillValidationResult,
    responses={404: {"description": "Skill not found"}},
    summary="Validate document against skill criteria",
)
def validate_skill(skill_id: str, payload: SkillTextRequest) -> SkillValidationResult:
    """Runs a specific skill's validation logic against input text."""
    skill = SkillRegistry.get(skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' is not registered.",
        )
    return skill.validate(payload.text, context=payload.context)


@router.post(
    "/{skill_id}/process",
    response_model=SkillExecutionResult,
    responses={404: {"description": "Skill not found"}},
    summary="Execute single skill transformation",
)
def process_skill(skill_id: str, payload: SkillTextRequest) -> SkillExecutionResult:
    """Executes a single skill's transformation rules on input text."""
    skill = SkillRegistry.get(skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' is not registered.",
        )
    return skill.process(payload.text, context=payload.context)


@router.post(
    "/pipeline",
    response_model=SkillOrchestrationResult,
    summary="Run text through enabled skills pipeline",
)
def run_pipeline(payload: SkillPipelineRequest) -> SkillOrchestrationResult:
    """Executes the pipeline on text according to enabled/disabled skill filters."""
    orchestrator = SkillOrchestrator()
    return orchestrator.run_pipeline(
        text=payload.text,
        enabled_skills=payload.enabled_skills,
        disabled_skills=payload.disabled_skills,
    )
