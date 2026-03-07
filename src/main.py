"""Main entry point for JARVIS bot."""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from .config import load_config
from .database.repository import Database
from .llm import OpenAIProvider, AnthropicProvider
from .gateways import DiscordGateway, Message
from .services import MatchParser, RoastGenerator
from .commands import (
    PartidoCommand,
    RankingCommand,
    StatsCommand,
    ActividadCommand,
    VoiceCommand,
    ServerCommand,
)


class JarvisBot:
    """Main JARVIS bot orchestrator."""

    def __init__(self):
        # Load configuration
        self.config = load_config()

        # Initialize database
        db_path = self.config.get("database", {}).get("path", "jarvis.db")
        self.db = Database(db_path)

        # Initialize LLM provider
        llm_config = self.config.get("llm", {})
        provider_name = llm_config.get("provider", "openai")
        model = llm_config.get("model", "gpt-4o-mini")

        if provider_name == "anthropic":
            self.llm = AnthropicProvider(model=model)
        else:
            self.llm = OpenAIProvider(model=model)

        print(f"✅ LLM Provider: {provider_name} ({model})")

        # Initialize services
        self.match_parser = MatchParser(self.llm)
        self.roast_generator = RoastGenerator(self.llm)

        # Initialize gateway
        gateway_config = self.config.get("gateways", {})
        if gateway_config.get("discord", {}).get("enabled", True):
            self.gateway = DiscordGateway(db=self.db)
        else:
            raise ValueError("No gateway enabled in config")

        # Initialize commands
        self.commands = {
            "/partido": PartidoCommand(
                self.db, self.gateway, self.match_parser, self.roast_generator
            ),
            "/ranking": RankingCommand(self.db, self.gateway),
            "/stats": StatsCommand(self.db, self.gateway, self.roast_generator),
            "/actividad": ActividadCommand(self.db, self.gateway),
            "/voice": VoiceCommand(self.db, self.gateway),
            "/server": ServerCommand(self.db, self.gateway),
        }

    async def handle_message(self, message: Message) -> None:
        """
        Handle incoming messages and route to appropriate commands.

        Args:
            message: The incoming message
        """
        content = message.content.strip()

        # Route to command handlers
        for cmd_prefix, handler in self.commands.items():
            if content.startswith(cmd_prefix):
                try:
                    await handler.handle(message)
                except Exception as e:
                    print(f"❌ Error handling {cmd_prefix}: {e}")
                    await self.gateway.send(
                        message.channel_id, f"I encountered an error: {str(e)}"
                    )
                return

        # Handle mentions
        bot_mentioned = (
            f"<@{self.gateway.client.user.id}>" in content
            or f"<@!{self.gateway.client.user.id}>" in content
        )

        if bot_mentioned:
            try:
                # Get recent conversation history from the channel
                conversation_history = self.gateway.memory.format_for_llm(
                    message.channel_id
                )

                # Generate a contextual response using the LLM
                if conversation_history:
                    response = await self.roast_generator.generate_contextual_response(
                        message.author_name, content, conversation_history
                    )
                else:
                    # Fallback to simple greeting if no history
                    response = await self.roast_generator.generate_greeting(
                        message.author_name
                    )

                await self.gateway.send(message.channel_id, response)
            except Exception as e:
                print(f"❌ Error handling mention: {e}")
                await self.gateway.send(
                    message.channel_id,
                    "At your service, sir. Though I must say, you interrupted my calculations.",
                )

    async def start(self) -> None:
        """Start the bot."""
        print("🤖 Starting JARVIS bot...")

        # Connect to database
        await self.db.connect()
        print("✅ Database connected")

        # Start gateway
        print("🚀 Starting gateway...")
        await self.gateway.start(self.handle_message)

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        print("🛑 Stopping JARVIS bot...")
        await self.gateway.stop()
        await self.db.close()
        print("👋 Goodbye")


async def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("LLM_API_KEY"):
        print("⚠️  Warning: LLM_API_KEY not set. LLM features will not work.")

    if not os.getenv("DISCORD_TOKEN"):
        print("⚠️  Warning: DISCORD_TOKEN not set. Discord gateway will not work.")

    # Create and start bot
    bot = JarvisBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n⚠️  Received keyboard interrupt")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise
    finally:
        await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye")
        sys.exit(0)
