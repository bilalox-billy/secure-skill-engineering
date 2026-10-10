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

