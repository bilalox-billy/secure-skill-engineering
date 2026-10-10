# tests/test_token_budget.py

import pytest
from src.token_budget import TokenBudgetManager, BudgetResult


class TestTokenBudgetManager:

    def test_estimate_tokens_empty_string(self):
        """Empty string should estimate 0 tokens."""
        mgr = TokenBudgetManager()
        assert mgr.estimate_tokens("") == 0

    def test_estimate_tokens_approximation(self):
        """400 characters ≈ 100 tokens."""
        mgr = TokenBudgetManager()
        text = "a" * 400
        assert mgr.estimate_tokens(text) == 100

    def test_check_budget_fits_short_prompt(self):
        """A short prompt should fit within any model's context."""
        mgr = TokenBudgetManager()
        result = mgr.check_budget(
            system_prompt="You are helpful.",
            user_message="Summarize: hello world.",
            model="llama3.2:3b",
            response_reserve=512
        )
        assert result.fits is True
        assert result.overflow_by == 0

    def test_check_budget_fails_for_huge_input(self):
        """A 100,000-character prompt should exceed any model's context."""
        mgr = TokenBudgetManager()
        huge_text = "x" * 100_000
        result = mgr.check_budget(
            system_prompt=huge_text,
            user_message="hello",
            model="gemma3:2b",  # 4096 token limit
            response_reserve=512
        )
        assert result.fits is False
        assert result.overflow_by > 0

    def test_get_context_limit_known_model(self):
        """Known model should return its specific limit."""
        mgr = TokenBudgetManager()
        assert mgr.get_context_limit("llama3.2:3b") == 8192
        assert mgr.get_context_limit("gemma3:2b") == 4096

    def test_get_context_limit_unknown_model_returns_default(self):
        """Unknown model should return the conservative default."""
        mgr = TokenBudgetManager()
        limit = mgr.get_context_limit("some-unknown-model:42b")
        assert limit == 4096  # DEFAULT_CONTEXT_LIMIT

    def test_truncate_text_short_text_unchanged(self):
        """Text under the limit should not be modified."""
        mgr = TokenBudgetManager()
        text = "short"
        result = mgr.truncate_text(text, max_tokens=1000)
        assert result == text

    def test_truncate_text_long_text_gets_note(self):
        """Text over the limit should be truncated and get a truncation note."""
        mgr = TokenBudgetManager()
        long_text = "a" * 10_000
        result = mgr.truncate_text(long_text, max_tokens=10)
        assert "[... document truncated" in result
        assert len(result) < len(long_text)
