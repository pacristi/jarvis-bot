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
from .tools import TOOLS, ToolExecutor


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

        # Initialize tools system
        self.tool_executor = ToolExecutor(
            self.db, self.gateway, self.match_parser, self.roast_generator
        )

    async def handle_message(self, message: Message) -> None:
        """
        Handle incoming messages - responds to ANY mention using tools.

        Args:
            message: The incoming message
        """
        content = message.content.strip()

        # Handle mentions
        if not self.gateway.client.user:
            return

        bot_mentioned = (
            f"<@{self.gateway.client.user.id}>" in content
            or f"<@!{self.gateway.client.user.id}>" in content
        )

        if bot_mentioned:
            try:
                await self._handle_mention(message)
            except Exception as e:
                print(f"❌ Error handling mention: {e}")
                import traceback

                traceback.print_exc()
                await self.gateway.send(
                    message.channel_id,
                    "At your service, sir. Though I must say, you interrupted my calculations.",
                )

    async def _handle_mention(self, message: Message) -> None:
        """Handle mention with LLM and tools."""
        # Get recent conversation history
        conversation_history = self.gateway.memory.format_for_llm(message.channel_id)

        # Build JARVIS system prompt with history
        system_prompt = """Bot de stats para Discord. Casual, directo.

Reglas:
- Máximo 1-2 líneas
- Pocas muletillas (no spamear "wn" en cada mensaje)
- Sin frases de boomer
- Ligeramente irónico

Ejemplos: "0 wins, rough" / "3h en voice, 0 wins" / "sin datos por acá"

Tienes tools para stats. Úsalas cuando pidan datos."""

        if conversation_history:
            system_prompt += f"\n\n{conversation_history}"

        # Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{message.author_name}: {message.content}"},
        ]

        # Call LLM with tools
        if hasattr(self.llm, "chat_with_tools"):
            text_response, tool_calls = await self.llm.chat_with_tools(
                messages=messages, tools=TOOLS, temperature=0.8
            )

            # If there are tool calls, execute them and continue conversation
            if tool_calls:
                # Execute all tool calls
                tool_results = []
                self.tool_executor._current_message = message  # Pass message context
                for tool_call in tool_calls:
                    result = await self.tool_executor.execute(
                        tool_call["name"], tool_call["input"]
                    )
                    tool_results.append(
                        {"tool_call_id": tool_call["id"], "result": result}
                    )

                # Build proper Anthropic message format for tool use continuation
                # Add assistant's tool use
                tool_use_content = []
                if text_response:
                    tool_use_content.append({"type": "text", "text": text_response})

                for tc in tool_calls:
                    tool_use_content.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["input"],
                        }
                    )

                # Remove system message for continuation
                continuation_messages = [
                    msg for msg in messages if msg["role"] != "system"
                ]
                continuation_messages.append(
                    {"role": "assistant", "content": tool_use_content}
                )

                # Add tool results
                tool_result_content = []
                for tr in tool_results:
                    tool_result_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tr["tool_call_id"],
                            "content": str(tr["result"]),
                        }
                    )

                continuation_messages.append(
                    {"role": "user", "content": tool_result_content}
                )

                # Get final response with tool results
                # We need to use the Anthropic client directly for this
                system_msg = next(
                    (m["content"] for m in messages if m["role"] == "system"), None
                )
                response = await self.llm.client.messages.create(
                    model=self.llm.model,
                    max_tokens=2048,
                    system=system_msg,
                    messages=continuation_messages,
                    temperature=0.8,
                )

                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text

                await self.gateway.send(message.channel_id, final_text)
            elif text_response:
                # Direct response without tools
                await self.gateway.send(message.channel_id, text_response)
            else:
                # Fallback
                await self.gateway.send(
                    message.channel_id, "At your service. How may I assist you today?"
                )
        else:
            # Fallback to simple chat without tools (for OpenAI or other providers)
            response = await self.llm.chat(messages, temperature=0.8)
            await self.gateway.send(message.channel_id, response)

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
