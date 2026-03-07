"""Anthropic LLM provider implementation."""

import os
from typing import Optional, Any
from anthropic import AsyncAnthropic

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) implementation of LLM provider."""

    def __init__(
        self, model: str = "claude-3-5-haiku-20241022", api_key: Optional[str] = None
    ):
        """
        Initialize Anthropic provider.

        Args:
            model: Model name (default: claude-3-5-haiku-20241022)
            api_key: Anthropic API key (defaults to LLM_API_KEY env var)
        """
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key or os.getenv("LLM_API_KEY"))

    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Send a chat completion request to Anthropic."""
        # Convert OpenAI-style messages to Anthropic format
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

        kwargs = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": anthropic_messages,
            "temperature": temperature,
        }

        if system_message:
            kwargs["system"] = system_message

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> tuple[Optional[str], Optional[list[dict[str, Any]]]]:
        """
        Send a chat completion request with tools support.

        Args:
            messages: List of message dictionaries
            tools: List of tool definitions in Anthropic format
            temperature: Temperature for response generation

        Returns:
            Tuple of (text_response, tool_calls)
            - text_response: Text content if present
            - tool_calls: List of tool calls if any, each with 'name' and 'input'
        """
        # Convert OpenAI-style messages to Anthropic format
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

        kwargs = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": anthropic_messages,
            "temperature": temperature,
            "tools": tools,
        }

        if system_message:
            kwargs["system"] = system_message

        response = await self.client.messages.create(**kwargs)

        # Extract text and tool calls
        text_response = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_response = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {"id": block.id, "name": block.name, "input": block.input}
                )

        return text_response, tool_calls if tool_calls else None

    async def vision(
        self, image_url: str, prompt: str, temperature: float = 0.7
    ) -> str:
        """Analyze an image using Anthropic's vision capabilities."""
        # For Claude, we need to handle images differently
        # If it's a URL, we need to fetch and encode it as base64
        # For now, we'll use the simpler approach with URLs if supported

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "url", "url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=messages,
            temperature=temperature,
        )
        return response.content[0].text
