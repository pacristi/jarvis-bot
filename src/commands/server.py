"""Command to show overall server stats."""

from ..database.repository import Database
from ..gateways.base import Gateway, Message


class ServerCommand:
    """Show overall server statistics."""
    
    def __init__(self, db: Database, gateway: Gateway):
        """
        Initialize the server command.
        
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
        Handle /server command.
        
        Shows overall server statistics combining matches, voice, and messages.
        
        Usage:
            /server - Show complete server stats
        """
        # Get server stats
        server_stats = await self.db.get_server_stats()
        
        total_players = server_stats.get('total_players', 0)
        total_matches = server_stats.get('total_matches', 0)
        total_voice = server_stats.get('total_voice_sessions', 0)
        total_messages = server_stats.get('total_messages', 0)
        
        # Get top performers
        match_ranking = await self.db.get_ranking(limit=3)
        voice_ranking = await self.db.get_voice_leaderboard(limit=3)
        message_ranking = await self.db.get_message_leaderboard(limit=3)
        
        # Build comprehensive response
        response = "**🤖 JARVIS Server Analysis Report**\n\n"
        response += "**Overview**\n"
        response += f"👥 Total players tracked: **{total_players}**\n"
        response += f"🎮 Matches recorded: **{total_matches:,}**\n"
        response += f"🎙️ Voice sessions: **{total_voice:,}**\n"
        response += f"💬 Messages sent: **{total_messages:,}**\n\n"
        
        # Top match winner
        if match_ranking:
            top_player = match_ranking[0]
            response += "**🏆 Top Match Winner**\n"
            response += f"{top_player['display_name']} - {top_player['wins']} wins "
            response += f"({top_player['total_matches']} matches)\n\n"
        
        # Top voice user
        if voice_ranking:
            top_voice = voice_ranking[0]
            total_secs = top_voice.get('total_seconds', 0) or 0
            response += "**🎙️ Most Vocal**\n"
            response += f"{top_voice['display_name']} - {self._format_duration(int(total_secs))} "
            response += f"({top_voice['total_sessions']} sessions)\n\n"
        
        # Top message sender
        if message_ranking:
            top_msg = message_ranking[0]
            response += "**💬 Most Chatty**\n"
            response += f"{top_msg['display_name']} - {top_msg['total_messages']:,} messages\n\n"
        
        # JARVIS commentary
        response += "---\n\n"
        
        if total_matches == 0 and total_messages == 0:
            response += "*Quite the ghost town, sir. Perhaps they're all too busy being productive elsewhere.*"
        elif total_matches > 100:
            response += "*Impressive dedication to avoiding productivity, I must say. "
            response += "One wonders if any actual work gets done here.*"
        elif total_messages > 10000:
            response += "*Such verbosity. If only the quantity of words matched the quality of ideas.*"
        elif total_voice > 1000:
            response += "*Remarkable social activity. A functioning community, or merely procrastination central?*"
        else:
            response += "*Moderate activity levels detected. The server lives, though barely.*"
        
        await self.gateway.send(message.channel_id, response)
