"""OpenAI LLM provider implementation."""

import os
from typing import Optional
from openai import AsyncOpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            model: Model name (default: gpt-4o-mini)
            api_key: OpenAI API key (defaults to LLM_API_KEY env var)
        """
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("LLM_API_KEY"))
    
    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Send a chat completion request to OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    
    async def vision(self, image_url: str, prompt: str, temperature: float = 0.7) -> str:
        """Analyze an image using OpenAI's vision capabilities."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ]
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # Use vision-capable model
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
