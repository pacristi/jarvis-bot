"""Service for parsing match screenshots using LLM vision."""

import json
from typing import Optional
from pydantic import BaseModel

from ..llm.base import LLMProvider


class ParsedMatch(BaseModel):
    """Parsed match data from screenshot."""
    
    game_name: str
    rankings: list[dict]  # [{player: str, position: int, score: Optional[int]}]
    

class MatchParser:
    """Parse match screenshots using LLM vision capabilities."""
    
    def __init__(self, llm: LLMProvider):
        self.llm = llm
    
    async def parse_screenshot(self, image_url: str) -> ParsedMatch:
        """
        Parse a match screenshot to extract game name and player rankings.
        
        Args:
            image_url: URL of the screenshot
            
        Returns:
            ParsedMatch with game name and rankings
        """
        prompt = """Analyze this game screenshot and extract the following information in JSON format:

{
  "game_name": "Name of the game (e.g., 'Pummel Party', 'Among Us', etc.)",
  "rankings": [
    {"player": "Player Name", "position": 1, "score": 123},
    {"player": "Player Name", "position": 2, "score": 98},
    ...
  ]
}

Rules:
- Extract player names exactly as shown
- Position is their rank (1st, 2nd, 3rd, etc.)
- Score is optional, only include if visible
- Order rankings by position (1st place first)
- Only include visible players

Return ONLY valid JSON, no additional text."""

        response = await self.llm.vision(image_url, prompt, temperature=0.3)
        
        # Try to extract JSON from response
        try:
            # Clean up response if it has markdown formatting
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            return ParsedMatch(**data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse LLM response: {response}") from e
