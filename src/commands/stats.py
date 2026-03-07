"""Command handler for /stats - show individual player statistics."""

import re
from typing import Optional

from ..database.repository import Database
from ..gateways.base import Gateway, Message
from ..services.roast_generator import RoastGenerator


class StatsCommand:
    """Handle /stats command to show player statistics."""
    
    def __init__(self, db: Database, gateway: Gateway, roast_generator: RoastGenerator):
        self.db = db
        self.gateway = gateway
        self.roast_generator = roast_generator
    
    async def handle(self, message: Message) -> None:
        """
        Handle /stats command.
        
        Expected usage: 
        - /stats - shows stats for the command sender
        - /stats @user - shows stats for mentioned user
        - /stats [game_name] - shows stats for specific game
        """
        content = message.content.strip()
        
        # Extract Discord mention if present (format: <@123456789>)
        mention_match = re.search(r'<@!?(\d+)>', content)
        
        if mention_match:
            target_discord_id = mention_match.group(1)
            # Remove mention from content to check for game name
            content = re.sub(r'<@!?\d+>', '', content).strip()
        else:
            target_discord_id = message.author_id
        
        # Parse game name if provided (after /stats and optional mention)
        parts = content.split(maxsplit=1)
        game_name = parts[1] if len(parts) > 1 else None
        
        # Get player from database
        player = await self.db.get_player_by_discord_id(target_discord_id)
        
        if not player:
            await self.gateway.send(
                message.channel_id,
                "I have no records for this player. Perhaps they should... participate?"
            )
            return
        
        # Get player stats
        stats = await self.db.get_player_stats(player.id, game_name=game_name)
        
        if not stats or stats.get("total_matches", 0) == 0:
            game_text = f" for {game_name}" if game_name else ""
            await self.gateway.send(
                message.channel_id,
                f"No matches recorded{game_text} for {player.display_name}."
            )
            return
        
        # Format stats message
        total_matches = stats.get("total_matches", 0)
        wins = stats.get("wins", 0)
        avg_position = stats.get("avg_position", 0)
        avg_score = stats.get("avg_score")
        
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        
        title = f"**Stats for {player.display_name}**"
        if game_name:
            title += f" ({game_name})"
        
        lines = [
            title,
            "",
            f"📊 Total Matches: {total_matches}",
            f"🏆 Wins: {wins} ({win_rate:.1f}%)",
            f"📍 Average Position: {avg_position:.1f}",
        ]
        
        if avg_score is not None:
            lines.append(f"⭐ Average Score: {avg_score:.1f}")
        
        await self.gateway.send(message.channel_id, "\n".join(lines))
        
        # Generate a roast comment if performance is... notable
        if total_matches >= 3:
            # Get player's rank for more context
            rankings = await self.db.get_ranking(game_name=game_name, limit=100)
            rank = next((i for i, r in enumerate(rankings, 1) if r["id"] == player.id), None)
            
            if rank:
                roast = await self.roast_generator.generate_ranking_roast(
                    player_name=player.display_name,
                    rank=rank,
                    stats=stats
                )
                await self.gateway.send(message.channel_id, f"\n{roast}")
