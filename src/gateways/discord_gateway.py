"""Discord gateway implementation."""

import os
import discord
from typing import Optional, Callable, Any
from discord import Intents, ButtonStyle
from discord.ui import View, Button

from .base import Gateway, Message


class DiscordGateway(Gateway):
    """Discord implementation of Gateway using discord.py."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Discord gateway.
        
        Args:
            token: Discord bot token (defaults to DISCORD_TOKEN env var)
        """
        self.token = token or os.getenv("DISCORD_TOKEN")
        
        # Setup intents
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        
        self.client = discord.Client(intents=intents)
        self.handler: Optional[Callable[[Message], Any]] = None
        
        # Register Discord event handlers
        @self.client.event
        async def on_ready():
            print(f"✅ Discord bot logged in as {self.client.user}")
        
        @self.client.event
        async def on_message(discord_message: discord.Message):
            # Ignore bot's own messages
            if discord_message.author == self.client.user:
                return
            
            # Convert Discord message to unified Message format
            image_url = None
            if discord_message.attachments:
                # Get first image attachment
                for attachment in discord_message.attachments:
                    if attachment.content_type and attachment.content_type.startswith("image/"):
                        image_url = attachment.url
                        break
            
            msg = Message(
                channel_id=str(discord_message.channel.id),
                author_id=str(discord_message.author.id),
                author_name=discord_message.author.display_name,
                content=discord_message.content,
                image_url=image_url,
                raw_message=discord_message
            )
            
            # Call registered handler
            if self.handler:
                await self.handler(msg)
    
    async def send(
        self,
        channel_id: str,
        message: str,
        buttons: Optional[list[dict]] = None
    ) -> None:
        """
        Send a message to a Discord channel.
        
        Args:
            channel_id: Discord channel ID
            message: Message text
            buttons: List of button configs with 'label', 'custom_id', 'style'
        """
        channel = self.client.get_channel(int(channel_id))
        if not channel:
            print(f"⚠️  Channel {channel_id} not found")
            return
        
        view = None
        if buttons:
            view = View()
            for btn_config in buttons:
                style = ButtonStyle.primary
                if btn_config.get("style") == "success":
                    style = ButtonStyle.success
                elif btn_config.get("style") == "danger":
                    style = ButtonStyle.danger
                
                button = Button(
                    label=btn_config["label"],
                    custom_id=btn_config.get("custom_id"),
                    style=style
                )
                view.add_item(button)
        
        await channel.send(message, view=view)
    
    async def start(self, handler: Callable[[Message], Any]) -> None:
        """
        Start the Discord bot.
        
        Args:
            handler: Async function to handle incoming messages
        """
        self.handler = handler
        await self.client.start(self.token)
    
    async def stop(self) -> None:
        """Stop the Discord bot."""
        await self.client.close()
