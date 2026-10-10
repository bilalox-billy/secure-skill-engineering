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

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
        description="ISO 8601 timestamp of when the request was made"
    )

    dry_run: bool = Field(
        default=True,
        description="If True, the skill will not be executed and will return debug information only"

    )

    model_config = {
        "extra": "forbid", # Reject unkown fields
        "str_strip_whitespace": True, # Auto-strip leading/trailing whitespace 
    }

# Skill-Specific Models

class DocumentSummarizerInput(BaseSkillInput):
    """Input model for the document-summarizer Skill.
    
    Validates:
      - document_text must be non-empty and at least 10 characters
      - max_length must be between 50 and 2000 words
    """

    document_text: str =Field(
        ..., # ... means required
        min_length=10,
        description="The document text to summarize"
    )

    max_length: int = Field(
        default=500,
        ge=50, # Greater than or equal to 50
        le=2000, # Less than or equal to 2000
        description="The maximum number of words in the summary"
    )

    @field_validator("document_text")
    @classmethod
    def document_must_not_be_only_whitespace(cls, v: str) -> str:
        """Strip Whitespaces then check it's not empty."""
        if not v.strip():
            raise ValueError("Document text must not be empty or only whitespace")
        return v


class CodeReviewerInput(BaseSkillInput):
    """Input Model for the code-reviewer Skill."""

