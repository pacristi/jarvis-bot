"""Pydantic models for database entities."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Player(BaseModel):
    """Player in the server."""
    
    id: Optional[int] = None
    discord_id: str
    display_name: str
    created_at: Optional[datetime] = None


class PlayerNickname(BaseModel):
    """Nickname used by a player in games."""
    
    id: Optional[int] = None
    player_id: int
    nickname: str


class LinkedAccount(BaseModel):
    """External account linked to a player."""
    
    id: Optional[int] = None
    player_id: int
    platform: str  # "riot", "steam", "epic"
    game_id: str
    linked_at: Optional[datetime] = None


class Match(BaseModel):
    """Match record for any game."""
    
    id: Optional[int] = None
    game_name: str
    played_at: Optional[datetime] = None
    screenshot_url: Optional[str] = None
    recorded_by: int


class Result(BaseModel):
    """Result for a player in a match."""
    
    id: Optional[int] = None
    match_id: int
    player_id: int
    position: int
    score: Optional[int] = None
    extra_data: Optional[str] = None  # JSON string


class VoiceSession(BaseModel):
    """Voice channel session for a player."""
    
    id: Optional[int] = None
    player_id: int
    channel_id: str
    channel_name: str
    joined_at: datetime
    left_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class MessageActivity(BaseModel):
    """Message activity tracking for a player."""
    
    id: Optional[int] = None
    player_id: int
    channel_id: str
    channel_name: str
    message_count: int = 1
    recorded_at: Optional[datetime] = None
