"""AI Provider module for LinkedIn Assistant Bot"""

from .base import AIProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .local_llm_provider import LocalLLMProvider

__all__ = [
    'AIProvider',
    'OpenAIProvider',
    'AnthropicProvider',
    'GeminiProvider',
    'LocalLLMProvider',
    'get_ai_provider'
]

def get_ai_provider(config: dict) -> AIProvider:
    """Factory function to get the appropriate AI provider based on config"""
    provider_name = config.get('ai_provider', 'openai').lower()

    providers = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'gemini': GeminiProvider,
        'local': LocalLLMProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown AI provider: {provider_name}. Choose from: {list(providers.keys())}")

    provider_class = providers[provider_name]
    return provider_class(config)
