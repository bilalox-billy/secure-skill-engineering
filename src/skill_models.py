# src/skill_models.py
"""
Pydantic input models for all four Skills.

Design pattern:
  BaseSkillInput defines common fields shared by all Skills.
  Each Skill-specific model adds its own fields with appropriate validators.

Key design decisions:
  - request_id auto-generated (no user input required)
  - dry_run=True skips Ollama call — returns debug info only
  - Strict validators reject bad input before wasting LLM tokens
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator



class BaseSkillInput(BaseModel):
    """Common fields for all Skill inputs.
    
    request_id and timestamp are auto-generated — callers don't set them.
    dry_run=True lets you test the pipeline without calling the LLM.
    """

    # auto-generated fields
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this execution request"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp when the request was created"
    )
    dry_run: bool = Field(
        default=False,
        description="If True, skip LLM call and return prompt details only"
    )

    model_config = {
        "extra": "forbid",       # Reject unknown fields — strict contract
        "str_strip_whitespace": True,  # Auto-strip leading/trailing whitespace
    }



class DocumentSummarizerInput(BaseSkillInput):
    """Input model for the document-summarizer Skill.
    
    Validates:
      - document_text must be non-empty and at least 10 characters
      - max_length must be between 50 and 2000 words
    """
    document_text: str = Field(
        ...,   # ... means "required" in Pydantic
        min_length=10,
        description="The document text to summarize"
    )
    max_length: int = Field(
        default=200,
        ge=50,    # greater than or equal to 50
        le=2000,  # less than or equal to 2000
        description="Maximum word count for the summary"
    )

    @field_validator("document_text")
    @classmethod
    def document_must_not_be_only_whitespace(cls, v: str) -> str:
        """Strip whitespace then check it's not empty."""
        if not v.strip():
            raise ValueError("document_text cannot be only whitespace")
        return v


class CodeReviewerInput(BaseSkillInput):
    """Input model for the code-reviewer Skill."""

    ALLOWED_FOCUS_AREAS = {"bugs", "style", "security", "performance", "documentation"}

    code: str = Field(
        ...,
        min_length=1,
        description="Python source code to review"
    )
    review_focus: list[str] = Field(
        default_factory=list,
        description="Which aspects to focus on. Empty = review everything."
    )

    @field_validator("review_focus")
    @classmethod
    def focus_must_be_valid(cls, v: list[str]) -> list[str]:
        """Each focus area must be from the allowed set."""
        invalid = set(v) - cls.ALLOWED_FOCUS_AREAS
        if invalid:
            raise ValueError(
                f"Invalid focus areas: {invalid}. "
                f"Allowed: {cls.ALLOWED_FOCUS_AREAS}"
            )
        return v


class EntityExtractorInput(BaseSkillInput):
    """Input model for the entity-extractor Skill."""

    ALLOWED_ENTITY_TYPES = {"persons", "organizations", "locations", "dates"}

    text: str = Field(
        ...,
        min_length=1,
        description="Text to extract entities from"
    )
    entity_types: list[str] = Field(
        default_factory=lambda: list(EntityExtractorInput.ALLOWED_ENTITY_TYPES),
        description="Which entity types to extract"
    )

    @field_validator("entity_types")
    @classmethod
    def types_must_be_valid(cls, v: list[str]) -> list[str]:
        invalid = set(v) - cls.ALLOWED_ENTITY_TYPES
        if invalid:
            raise ValueError(f"Invalid entity types: {invalid}")
        return v if v else list(cls.ALLOWED_ENTITY_TYPES)


class ConceptMapperInput(BaseSkillInput):
    """Input model for the concept-mapper Skill."""

    document_text: str = Field(
        ...,
        min_length=20,
        description="Text to extract concepts from"
    )
    max_concepts: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of concepts to extract"
    )


class TaskInterpreterInput(BaseSkillInput):
    """Input model for the task-interpreter Skill (Day 7)."""

    user_request: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Natural language request from the user"
    )


# Registry: maps skill names to their input model

SKILL_INPUT_MODELS: dict[str, type[BaseSkillInput]] = {
    "document-summarizer": DocumentSummarizerInput,
    "code-reviewer": CodeReviewerInput,
    "entity-extractor": EntityExtractorInput,
    "concept-mapper": ConceptMapperInput,
    "task-interpreter": TaskInterpreterInput,
}
