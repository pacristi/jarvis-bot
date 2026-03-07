"""Command handler for /ranking - show leaderboard."""

from typing import Optional

from ..database.repository import Database
from ..gateways.base import Gateway, Message


class RankingCommand:
    """Handle /ranking command to show player leaderboard."""
    
    def __init__(self, db: Database, gateway: Gateway):
        self.db = db
        self.gateway = gateway
    
    async def handle(self, message: Message) -> None:
        """
        Handle /ranking command.
        
        Expected usage: 
        - /ranking - shows overall ranking
        - /ranking [game_name] - shows ranking for specific game
        """
        # Parse game name from message if provided
        parts = message.content.strip().split(maxsplit=1)
        game_name = parts[1] if len(parts) > 1 else None
        
        # Get ranking from database
        rankings = await self.db.get_ranking(game_name=game_name, limit=10)
        
        if not rankings:
            await self.gateway.send(
                message.channel_id,
                "No matches have been recorded yet. How... disappointing."
            )
            return
        
        # Format leaderboard message
        title = f"**Leaderboard: {game_name}**" if game_name else "**Overall Leaderboard**"
        
        lines = [title, ""]
        for i, rank in enumerate(rankings, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            
            name = rank["display_name"]
            wins = rank["wins"]
            total = rank["total_matches"]
            avg_pos = rank["avg_position"]
            
            win_rate = (wins / total * 100) if total > 0 else 0
            
            line = f"{medal} **{name}** - {wins} wins / {total} matches ({win_rate:.1f}% win rate, avg position: {avg_pos:.1f})"
            lines.append(line)
        
        await self.gateway.send(message.channel_id, "\n".join(lines))
