# src/failure_policy.py
"""
FailurePolicy: per-Skill configuration for handling execution failures.

Why failure policies?
  Different Skills have different acceptable failure modes:
  - A document summarizer can return partial output if schema validation fails
  - A code executor should hard-fail — partial output could be dangerous
  - A classification skill should retry once before giving up

This module lets you configure failure behavior per-Skill without
changing the executor logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FailureStrategy(str, Enum):
    """How the executor should handle a failed Skill execution."""
    RETRY_ONCE = "retry_once"          # Try one more time with same inputs
    PARTIAL_OUTPUT = "partial_output"  # Return partial result even if invalid
    HARD_FAIL = "hard_fail"            # Return failure, no partial output
    ESCALATE = "escalate"              # Flag for human review


@dataclass
class FailurePolicy:
    """Failure handling configuration for a single Skill.
    
    Attributes:
        strategy: The primary failure handling approach
        fallback_skill: Optional name of a simpler Skill to try if this one fails
        max_retries: How many times to retry before giving up
        escalate_on_consecutive: After N consecutive failures, escalate to human
    """
    strategy: FailureStrategy = FailureStrategy.RETRY_ONCE
    fallback_skill: str | None = None
    max_retries: int = 1
    escalate_on_consecutive: int = 3   # After 3 failures, escalate


# Default policies per Skill
# You can override these per deployment
DEFAULT_POLICIES: dict[str, FailurePolicy] = {
    "document-summarizer": FailurePolicy(
        strategy=FailureStrategy.RETRY_ONCE,
        max_retries=1,
    ),
    "entity-extractor": FailurePolicy(
        strategy=FailureStrategy.PARTIAL_OUTPUT,
        max_retries=1,
    ),
    "concept-mapper": FailurePolicy(
        strategy=FailureStrategy.RETRY_ONCE,
        fallback_skill="document-summarizer",
        max_retries=2,
    ),
    "code-reviewer": FailurePolicy(
        strategy=FailureStrategy.HARD_FAIL,   # Don't return partial code review
        max_retries=1,
    ),
}

DEFAULT_POLICY = FailurePolicy(strategy=FailureStrategy.RETRY_ONCE)


class FailurePolicyManager:
    """Manages and provides FailurePolicy objects for Skills.
    
    Usage:
        manager = FailurePolicyManager()
        policy = manager.get_policy("code-reviewer")
        if manager.should_retry("code-reviewer", attempt=1, error="timeout"):
            # try again
    """

    def __init__(self, policies: dict[str, FailurePolicy] | None = None):
        self.policies = policies or DEFAULT_POLICIES

    def get_policy(self, skill_name: str) -> FailurePolicy:
        """Return the policy for a skill, or the default policy if not registered."""
        return self.policies.get(skill_name, DEFAULT_POLICY)

    def should_retry(self, skill_name: str, attempt: int, error: str) -> bool:
        """Decide whether to retry after a failure.
        
        Args:
            skill_name: The Skill that failed
            attempt: Which attempt just failed (1-based)
            error: The error message (used to decide if retry makes sense)
        
        Returns:
            True if another attempt should be made.
        """
        policy = self.get_policy(skill_name)

        # Hard fail = never retry
        if policy.strategy == FailureStrategy.HARD_FAIL:
            return False

        # Don't retry if we've already reached max_retries
        if attempt >= policy.max_retries:
            return False

        # Don't retry connection errors (Ollama not running)
        # Retrying won't fix a connectivity issue
        if "connection refused" in error.lower() or "not running" in error.lower():
            return False

        # Don't retry model-not-found errors
        if "not installed" in error.lower() or "pull" in error.lower():
            return False

        return True
