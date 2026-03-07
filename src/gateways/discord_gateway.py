"""Discord gateway implementation."""

import os
import discord
from typing import Optional, Callable, Any
from discord import Intents, ButtonStyle
from discord.ui import View, Button

from .base import Gateway, Message
from ..database.repository import Database
from ..services import ConversationMemory


class DiscordGateway(Gateway):
    """Discord implementation of Gateway using discord.py."""

    def __init__(self, token: Optional[str] = None, db: Optional[Database] = None):
        """
        Initialize Discord gateway.

        Args:
            token: Discord bot token (defaults to DISCORD_TOKEN env var)
            db: Database instance for tracking activity
        """
        self.token = token or os.getenv("DISCORD_TOKEN")
        self.db = db
        self.memory = ConversationMemory(max_messages=15, max_age_minutes=30)

        # Setup intents
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

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

            # Save message to conversation memory
            self.memory.add_message(
                channel_id=str(discord_message.channel.id),
                author_name=discord_message.author.display_name,
                content=discord_message.content,
                is_bot=discord_message.author.bot,
            )

            # Track message activity in database
            if self.db and not discord_message.author.bot:
                try:
                    # Ensure player exists
                    player = await self.db.get_player_by_discord_id(
                        str(discord_message.author.id)
                    )
                    if not player:
                        player = await self.db.create_player(
                            str(discord_message.author.id),
                            discord_message.author.display_name,
                        )

                    # Record message
                    await self.db.record_message(
                        player.id,
                        str(discord_message.channel.id),
                        discord_message.channel.name
                        if hasattr(discord_message.channel, "name")
                        else "DM",
                    )
                except Exception as e:
                    print(f"⚠️  Error tracking message: {e}")

            # Convert Discord message to unified Message format
            image_url = None
            if discord_message.attachments:
                # Get first image attachment
                for attachment in discord_message.attachments:
                    if attachment.content_type and attachment.content_type.startswith(
                        "image/"
                    ):
                        image_url = attachment.url
                        break

            msg = Message(
                channel_id=str(discord_message.channel.id),
                author_id=str(discord_message.author.id),
                author_name=discord_message.author.display_name,
                content=discord_message.content,
                image_url=image_url,
                raw_message=discord_message,
            )

            # Call registered handler
            if self.handler:
                await self.handler(msg)

        @self.client.event
        async def on_voice_state_update(
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState,
        ):
            """Track voice channel activity."""
            if not self.db or member.bot:
                return

            try:
                # Ensure player exists
                player = await self.db.get_player_by_discord_id(str(member.id))
                if not player:
                    player = await self.db.create_player(
                        str(member.id), member.display_name
                    )

                # User left a voice channel
                if before.channel and not after.channel:
                    # End active session
                    session = await self.db.get_active_voice_session(
                        player.id, str(before.channel.id)
                    )
                    if session:
                        await self.db.end_voice_session(session.id)
                        print(f"🎙️  {member.display_name} left {before.channel.name}")

                # User joined a voice channel
                elif not before.channel and after.channel:
                    # Start new session
                    await self.db.start_voice_session(
                        player.id, str(after.channel.id), after.channel.name
                    )
                    print(f"🎙️  {member.display_name} joined {after.channel.name}")

                # User switched channels
                elif (
                    before.channel
                    and after.channel
                    and before.channel.id != after.channel.id
                ):
                    # End old session
                    old_session = await self.db.get_active_voice_session(
                        player.id, str(before.channel.id)
                    )
                    if old_session:
                        await self.db.end_voice_session(old_session.id)

                    # Start new session
                    await self.db.start_voice_session(
                        player.id, str(after.channel.id), after.channel.name
                    )
                    print(
                        f"🎙️  {member.display_name} moved from {before.channel.name} to {after.channel.name}"
                    )

            except Exception as e:
                print(f"⚠️  Error tracking voice state: {e}")

    async def send(
        self, channel_id: str, message: str, buttons: Optional[list[dict]] = None
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
                    style=style,
                )
                view.add_item(button)

        await channel.send(message, view=view)

        # Save bot's response to conversation memory
        bot_name = self.client.user.display_name if self.client.user else "JARVIS"
        self.memory.add_message(
            channel_id=channel_id, author_name=bot_name, content=message, is_bot=True
        )

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
