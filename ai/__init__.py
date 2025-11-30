"""AI Provider module for LinkedIn Assistant Bot"""

from .base import AIProvider

__all__ = [
    'AIProvider',
    'get_ai_provider'
]

def get_ai_provider(config: dict) -> AIProvider:
    """Factory function to get the appropriate AI provider based on config"""
    provider_name = config.get('ai_provider', 'openai').lower()

    # Lazy imports - only import when needed
    if provider_name == 'openai':
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(config)
    elif provider_name == 'anthropic':
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)
    elif provider_name == 'gemini':
        from .gemini_provider import GeminiProvider
        return GeminiProvider(config)
    elif provider_name == 'local':
        from .local_llm_provider import LocalLLMProvider
        return LocalLLMProvider(config)
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}. Choose from: openai, anthropic, gemini, local")
