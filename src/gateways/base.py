"""Abstract base class for gateway implementations."""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
from pydantic import BaseModel


class Message(BaseModel):
    """Unified message format across all gateways."""
    
    channel_id: str
    author_id: str
    author_name: str
    content: str
    image_url: Optional[str] = None
    raw_message: Optional[Any] = None  # Gateway-specific message object


class Gateway(ABC):
    """Abstract interface for messaging platform gateways."""
    
    @abstractmethod
    async def send(
        self, 
        channel_id: str, 
        message: str, 
        buttons: Optional[list[dict]] = None
    ) -> None:
        """
        Send a message to a channel.
        
        Args:
            channel_id: The channel/chat ID to send to
            message: The message text
            buttons: Optional list of button configs (gateway-specific format)
        """
        pass
    
    @abstractmethod
    async def start(self, handler: Callable[[Message], Any]) -> None:
        """
        Start the gateway and register message handler.
        
        Args:
            handler: Async function to handle incoming messages
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the gateway gracefully."""
        pass
