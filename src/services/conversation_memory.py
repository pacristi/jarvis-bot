"""Conversation memory for tracking recent messages per channel."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict


@dataclass
class ConversationMessage:
    """Represents a single message in conversation history."""

    author_name: str
    content: str
    timestamp: datetime
    is_bot: bool


class ConversationMemory:
    """Manages short-term conversation memory per channel."""

    def __init__(self, max_messages: int = 15, max_age_minutes: int = 30):
        """
        Initialize conversation memory.

        Args:
            max_messages: Maximum number of messages to keep per channel
            max_age_minutes: Maximum age of messages to keep (in minutes)
        """
        self.max_messages = max_messages
        self.max_age = timedelta(minutes=max_age_minutes)
        self._memory: dict[str, list[ConversationMessage]] = defaultdict(list)

    def add_message(
        self, channel_id: str, author_name: str, content: str, is_bot: bool = False
    ) -> None:
        """
        Add a message to the channel's conversation history.

        Args:
            channel_id: ID of the channel
            author_name: Name of the message author
            content: Message content
            is_bot: Whether the message is from a bot
        """
        message = ConversationMessage(
            author_name=author_name,
            content=content,
            timestamp=datetime.now(),
            is_bot=is_bot,
        )

        # Add message to channel history
        self._memory[channel_id].append(message)

        # Trim to max messages
        if len(self._memory[channel_id]) > self.max_messages:
            self._memory[channel_id] = self._memory[channel_id][-self.max_messages :]

        # Clean old messages
        self._cleanup_old_messages(channel_id)

    def get_recent_messages(
        self, channel_id: str, max_count: Optional[int] = None
    ) -> list[ConversationMessage]:
        """
        Get recent messages from a channel.

        Args:
            channel_id: ID of the channel
            max_count: Maximum number of messages to return (defaults to all)

        Returns:
            List of recent messages, ordered chronologically (oldest first)
        """
        # Clean old messages first
        self._cleanup_old_messages(channel_id)

        messages = self._memory.get(channel_id, [])

        if max_count is not None:
            messages = messages[-max_count:]

        return messages

    def format_for_llm(self, channel_id: str) -> str:
        """
        Format recent conversation history for LLM context.

        Args:
            channel_id: ID of the channel

        Returns:
            Formatted conversation history as a string
        """
        messages = self.get_recent_messages(channel_id)

        if not messages:
            return ""

        lines = ["Recent conversation history:"]
        for msg in messages:
            lines.append(f"- {msg.author_name}: {msg.content}")

        return "\n".join(lines)

    def _cleanup_old_messages(self, channel_id: str) -> None:
        """
        Remove messages older than max_age from a channel.

        Args:
            channel_id: ID of the channel
        """
        if channel_id not in self._memory:
            return

        now = datetime.now()
        cutoff_time = now - self.max_age

        # Filter out old messages
        self._memory[channel_id] = [
            msg for msg in self._memory[channel_id] if msg.timestamp >= cutoff_time
        ]

        # Remove channel if empty
        if not self._memory[channel_id]:
            del self._memory[channel_id]

    def clear_channel(self, channel_id: str) -> None:
        """
        Clear all messages from a channel.

        Args:
            channel_id: ID of the channel
        """
        if channel_id in self._memory:
            del self._memory[channel_id]

    def get_stats(self) -> dict:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory statistics
        """
        total_messages = sum(len(messages) for messages in self._memory.values())

        return {
            "channels": len(self._memory),
            "total_messages": total_messages,
            "avg_messages_per_channel": (
                total_messages / len(self._memory) if self._memory else 0
            ),
        }
