"""Command to show message activity stats."""

from ..database.repository import Database
from ..gateways.base import Gateway, Message


class ActividadCommand:
    """Show message activity statistics."""
    
    def __init__(self, db: Database, gateway: Gateway):
        """
        Initialize the actividad command.
        
        Args:
            db: Database instance
            gateway: Gateway for sending messages
        """
        self.db = db
        self.gateway = gateway
    
    async def handle(self, message: Message) -> None:
        """
        Handle /actividad command.
        
        Shows message activity stats for a user or the entire server.
        
        Usage:
            /actividad - Your own stats
            /actividad @user - Another user's stats
        """
        parts = message.content.strip().split()
        
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
                f"I have no records for {target_name}. Perhaps they should try speaking more often."
            )
            return
        
        # Get message stats
        stats = await self.db.get_message_stats(player.id)
        
        if stats.get('total_messages', 0) == 0:
            await self.gateway.send(
                message.channel_id,
                f"Curious. {target_name} appears to be a mute. Zero messages recorded, sir."
            )
            return
        
        # Build response
        total_msgs = stats.get('total_messages', 0)
        channels = stats.get('channels_used', 0)
        
        response = f"**Message Activity Report - {target_name}**\n\n"
        response += f"📊 Total messages: **{total_msgs:,}**\n"
        response += f"📺 Channels active in: **{channels}**\n"
        response += f"💬 Average per channel: **{total_msgs / channels if channels > 0 else 0:.1f}**\n\n"
        
        # Get leaderboard position
        leaderboard = await self.db.get_message_leaderboard(limit=100)
        position = None
        for i, entry in enumerate(leaderboard, 1):
            if entry['id'] == player.id:
                position = i
                break
        
        if position:
            response += f"🏆 Server rank: **#{position}**\n\n"
        
        # Add JARVIS commentary
        if position == 1:
            response += "*Most chatty, sir. One might say you have a lot to say. Or perhaps, too much.*"
        elif total_msgs > 1000:
            response += "*Quite the conversationalist. I trust the quality matches the quantity?*"
        elif total_msgs < 10:
            response += "*A person of few words. How refreshing, if somewhat suspicious.*"
        else:
            response += "*Moderate activity detected. Perfectly average, sir.*"
        
        await self.gateway.send(message.channel_id, response)
