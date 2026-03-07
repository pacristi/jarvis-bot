"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract interface for LLM providers (OpenAI, Anthropic, etc.)."""
    
    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            The assistant's response content
        """
        pass
    
    @abstractmethod
    async def vision(self, image_url: str, prompt: str, temperature: float = 0.7) -> str:
        """
        Analyze an image with a prompt.
        
        Args:
            image_url: URL or path to the image
            prompt: The prompt/question about the image
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            The assistant's analysis
        """
        pass
