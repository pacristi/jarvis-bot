"""Command to show voice activity stats."""

from ..database.repository import Database
from ..gateways.base import Gateway, Message


class VoiceCommand:
    """Show voice channel activity statistics."""
    
    def __init__(self, db: Database, gateway: Gateway):
        """
        Initialize the voice command.
        
        Args:
            db: Database instance
            gateway: Gateway for sending messages
        """
        self.db = db
        self.gateway = gateway
    
    def _format_duration(self, seconds: int) -> str:
        """Format seconds into human-readable duration."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    async def handle(self, message: Message) -> None:
        """
        Handle /voice command.
        
        Shows voice channel activity stats for a user or leaderboard.
        
        Usage:
            /voice - Your own stats
            /voice @user - Another user's stats
            /voice leaderboard - Top voice chatters
        """
        parts = message.content.strip().split()
        
        # Check if leaderboard is requested
        if len(parts) > 1 and parts[1].lower() == "leaderboard":
            await self._show_leaderboard(message)
            return
        
        # If mention is provided, extract discord_id from raw_message
        target_discord_id = None
        target_name = None
        
        if hasattr(message, 'raw_message') and message.raw_message.mentions:
            # Get first mentioned user
            mentioned_user = message.raw_message.mentions[0]
            target_discord_id = str(mentioned_user.id)
            target_name = mentioned_user.display_name
        else:
            # Use author's own stats
            target_discord_id = message.author_id
            target_name = message.author_name
        
        # Get player
        player = await self.db.get_player_by_discord_id(target_discord_id)
        if not player:
            await self.gateway.send(
                message.channel_id,
                f"I have no voice records for {target_name}. Perhaps they prefer the written word."
            )
            return
        
        # Get voice stats
        stats = await self.db.get_voice_stats(player.id)
        
        total_sessions = stats.get('total_sessions', 0)
        if total_sessions == 0:
            await self.gateway.send(
                message.channel_id,
                f"Curious. {target_name} has never graced our voice channels. A hermit, perhaps?"
            )
            return
        
        # Build response
        total_seconds = stats.get('total_seconds', 0) or 0
        avg_seconds = stats.get('avg_session_seconds', 0) or 0
        longest = stats.get('longest_session_seconds', 0) or 0
        
        response = f"**Voice Activity Report - {target_name}**\n\n"
        response += f"🎙️ Total sessions: **{total_sessions:,}**\n"
        response += f"⏱️ Total time: **{self._format_duration(int(total_seconds))}**\n"
        response += f"📊 Average session: **{self._format_duration(int(avg_seconds))}**\n"
        response += f"🏆 Longest session: **{self._format_duration(int(longest))}**\n\n"
        
        # Get leaderboard position
        leaderboard = await self.db.get_voice_leaderboard(limit=100)
        position = None
        for i, entry in enumerate(leaderboard, 1):
            if entry['id'] == player.id:
                position = i
                break
        
        if position:
            response += f"🏅 Server rank: **#{position}**\n\n"
        
        # Add JARVIS commentary
        hours = total_seconds / 3600
        if position == 1:
            response += "*Most vocal, sir. One wonders if you have anything else to do with your time.*"
        elif hours > 100:
            response += "*Quite the social butterfly. Or perhaps just unemployed?*"
        elif hours < 1:
            response += "*Brief appearances, I see. Quality over quantity, or just antisocial?*"
        else:
            response += "*Acceptable levels of social interaction detected, sir.*"
        
        await self.gateway.send(message.channel_id, response)
    
    async def _show_leaderboard(self, message: Message) -> None:
        """Show voice activity leaderboard."""
        leaderboard = await self.db.get_voice_leaderboard(limit=10)
        
        if not leaderboard:
            await self.gateway.send(
                message.channel_id,
                "No voice activity recorded yet. A server of mutes, it would seem."
            )
            return
        
        response = "**Voice Activity Leaderboard**\n\n"
        
        for i, entry in enumerate(leaderboard, 1):
            name = entry['display_name']
            total_seconds = entry['total_seconds'] or 0
            sessions = entry['total_sessions']
            
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            
            response += f"{medal} **#{i} {name}**\n"
            response += f"   ⏱️ {self._format_duration(int(total_seconds))} ({sessions} sessions)\n\n"
        
        response += "*The social hierarchy, as dictated by vocal presence. How democratic.*"
        
        await self.gateway.send(message.channel_id, response)
