# src/token_budget.py
"""
TokenBudgetManager: estimates and manages prompt token budgets.

Why token budgets?
  Every LLM has a context window limit (e.g., 8192 tokens for llama3.2:3b).
  If your prompt + response exceeds this, the model silently truncates input.
  Token budget management prevents this silently broken behavior.

Character-based estimation:
  Exact token counting requires the model's tokenizer.
  As a practical approximation: 1 token ≈ 4 English characters.
  This is imprecise (±20%) but sufficient for budget checks.
  For exact counts, integrate with tiktoken (OpenAI's tokenizer) later.
"""


from __future__ import annotations
from dataclasses import dataclass

@dataclass
class BudgetResult:
    """Result of a token budget check.
    
    fits=True means the prompt should be within the model's context window.
    overflow_by shows how many estimated tokens exceed the limit (if fits=False).
    """

    fits: bool
    estimated_input_tokens: int
    reserved_for_response: int
    context_limit: int
    available_for_response: int # How many tokens are left after input
    overflow_by: int = 0 # 0 if fits = True


# Known context limits for common Ollama models
# These are approximate — check Ollama model cards for exact values
MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "llama3.2:3b": 8192,
    "llama3.2:1b": 8192,
    "llama3.1:8b": 8192,
    "llama3.1:70b": 8192,
    "mistral:7b": 8192,
    "mistral:latest": 8192,
    "gemma3:2b": 4096,
    "gemma3:9b": 8192,
    "qwen2.5:7b": 8192,
    "qwen2.5:14b": 8192,
    "phi3:mini": 4096,
    "phi3:medium": 4096,
}

DEFAULT_CONTEXT_LIMIT: int = 4096  # Conservative default for unknown models
CHARS_PER_TOKEN: int = 4 # Approximate: 1 token ≈ 4 English characters


class TokenBudgetManager:

    """Estimates token usage and checks if prompts fit within model limits.
    
    Usage:
        manager = TokenBudgetManager()
        result = manager.check_budget(
            system_prompt="You are...",
            user_message="Summarize this: ...",
            model="llama3.2:3b",
            response_reserve=512
        )
        if not result.fits:
            print(f"Overflow by {result.overflow_by} tokens!")
    """

    def __init__(self, custom_limit: dict[str, str] | None = None):
        """
        Args:
            custom_limits: Override or extend the default model context limits.
        """

        self.limits = {**MODEL_CONTEXT_LIMITS}

        if custom_limit:
            self.limits.update(custom_limit)
        
    
    def estimate_tokens(self, text: str) -> int:

        """Estimate token count from character count.
        
        This is an approximation. Real token counts depend on the model's
        specific tokenizer. For English text, 1 token ≈ 4 characters.
        
        Args:
            text: Any string (prompt text, document, etc.)
        
        Returns:
            Estimated number of tokens.
        """

        if not text:
            return 0
        
        return max(1, len(text) // CHARS_PER_TOKEN)

    
    def get_context_limit(self, model: str) -> int:
        """Get the context token limit for a model name.
        
        Handles model name variants like "llama3.2:3b" vs "llama3.2".
        Falls back to DEFAULT_CONTEXT_LIMIT for unknown models.
        """

        if model in self.limits:
            return self.limits[model]
        
        # Partial match (e.g., "llama3.2" matches "llama3.2:3b")
        for known_model, limit in self.limits.items():
            if model in known_model or known_model in model:
                return limit
        
        # No exact match: use DEFAULT_CONTEXT_LIMIT
        return DEFAULT_CONTEXT_LIMIT


    def check_budget(
        self,
        system_prompt: str,
        user_message: str,
        model: str = "llama3.2:3b",
        response_reserve: int = 512,
    ) -> BudgetResult:
        """Check if a prompt fits within the model's context window.
        
        Args:
            system_prompt: The system message content
            user_message: The user message content
            model: The Ollama model name
            response_reserve: Tokens to reserve for the model's response
        
        Returns:
            BudgetResult with fits=True if the total fits within the context.
        """

        context_limit = self.get_context_limit(model)

        system_tokens = self.estimate_tokens(system_prompt)
        user_tokens = self.estimate_tokens(user_message)
        total_input_tokens = system_tokens + user_tokens

        available_for_response = context_limit - total_input_tokens
        fits = available_for_response >= response_reserve

        overflow_by = max(0, response_reserve - available_for_response)

        return BudgetResult(
            fits=fits,
            estimated_input_tokens=total_input_tokens,
            reserved_for_response=response_reserve,
            context_limit=context_limit,
            available_for_response=available_for_response,
            overflow_by=overflow_by,
        )

    
    def truncate_text(
        self,
        text: str,
        max_tokens: int,
        truncation_note: str = "\n\n[... document truncated to fit context window ...]",
    ) -> str:
        """Truncate text to fit within max_tokens.
        
        Adds a truncation note so the LLM knows the text was cut.
        
        Args:
            text: The text to potentially truncate
            max_tokens: Maximum tokens allowed
            truncation_note: Text appended to signal truncation
        
        Returns:
            Original text if it fits, or truncated text + note if not.
        """
        max_chars = max_tokens * CHARS_PER_TOKEN
        note_chars = len(truncation_note)

        if len(text) <= max_chars:
            return text  # No truncation needed

        # Reserve space for the note (clamp to 0 so a negative value
        # never turns into a Python "slice from the end" index)
        keep_chars = max(0, max_chars - note_chars)
        return text[:keep_chars] + truncation_note










