# src/input_validator.py
"""
InputValidator: validates raw input dicts using Pydantic models.

Why a separate class instead of calling Pydantic directly?
  - Centralizes the skill-name → model mapping
  - Provides a consistent return type (InputValidationResult)
  - Handles Skills with no registered model gracefully
  - Converts Pydantic's verbose errors to readable messages
"""

from __future__ import annotations
from dataclasses import dataclass, field
import pydantic

from src.skill_models import SKILL_INPUT_MODELS, BaseSkillInput



@dataclass
class InputValidationResult:
    """Result of input validation.
    
    valid=True means validated_input is safe to use.
    validated_input is the Pydantic model instance (has auto-filled defaults).
    errors contains human-readable descriptions if valid=False.
    skipped=True means no model was registered for this skill.
    """
    valid: bool
    validated_input: BaseSkillInput | dict | None = None
    errors: list[str] = field(default_factory=list)
    skipped: bool = False #True if no model registered for this skill



class InputValidator:

    """Validates Skill inputs using registered Pydantic models.
    
    Usage:
        validator = InputValidator()
        result = validator.validate("document-summarizer", {
            "document_text": "Hello world",
            "max_length": 100
        })
        if result.valid:
            validated = result.validated_input
            print(validated.document_text)   # type-safe access
        else:
            print(result.errors)
    """

    def __init__(self, models: dict[str, type] | None = None):
        # Allow injecting custom models (for testing)
        self.models = models or SKILL_INPUT_MODELS

    def validate(self, skill_name: str, raw_input: dict) -> InputValidationResult:
        """Validate raw_inputs against the registered model for skill_name.
        
        If no model is registered, validation is skipped (not failed).
        This allows new Skills to be added without immediately requiring models.
        """

        model_class  = self.models.get(skill_name)
        if model_class is None:
            # No model registered: skip validation, pass input through
            return InputValidationResult(
                valid=True,
                validated_input=raw_input,
                skipped=True,
            )
        
        try:
            # Pydantic validates and contsructs the model
            # model_vaidate() is pyodantic's model_validator
            instance = model_class.model_validate(raw_input)
            return InputValidationResult(valid=True, validated_input=instance)
        
        except pydantic.ValidationError as e:
            # Convert pydantic error structure to readable messages
            errors = self._format_pydantic_errors(e)
            return InputValidationResult(valid=False, errors=errors)
        
    
    def _format_pydantic_errors(self, error: pydantic.ValidationError) -> list[str]:
        """Convert Pydantic ValidationError into readable error strings.
        
        Pydantic v2 errors have: loc (field path), msg (message), type (error code)
        """
        messages = []
        for err in error.errors():
            # loc is a tuple of field names/indices, e.g., ('document_text',)
            field_path = " -> ".join(str(part) for part in err["loc"])
            message = err["msg"]
            messages.append(f"Field '{field_path}': {message}")
        return message

    def get_model_schema(self, skill_name: str) -> dict | None:
        """Return the JSON Schema generated from the Pydantic model.
        
        Useful for documentation and input format guidance.
        """
        model_class = self.models.get(skill_name)
        if model_class is None:
            return None
        return model_class.model_json_schema()       

