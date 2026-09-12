"""
Singleton Anthropic client — one instance for the lifetime of the process.
Import _get_client() from here instead of instantiating anthropic.Anthropic() directly.
"""

import anthropic
from mini_bloomberg.config import get_settings

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        _client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )
    return _client
