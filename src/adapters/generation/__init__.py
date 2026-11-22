"""Generation adapters for LLM inference and offline test doubles."""

from src.adapters.generation.litellm_adapter import LiteLLMGenerationAdapter
from src.adapters.generation.mock_adapter import MockGenerationAdapter

__all__ = ["LiteLLMGenerationAdapter", "MockGenerationAdapter"]
