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
from .services import MatchParser, RoastGenerator, PlayerMemory
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
        self.player_memory = PlayerMemory("player_memories.json")

        # Initialize gateway
        gateway_config = self.config.get("gateways", {})
        if gateway_config.get("discord", {}).get("enabled", True):
            self.gateway = DiscordGateway(db=self.db)
        else:
            raise ValueError("No gateway enabled in config")

        # Initialize tools system
        self.tool_executor = ToolExecutor(
            self.db, self.gateway, self.match_parser, self.roast_generator, self.player_memory
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
        # Load persistent conversation history for this user in this channel
        persistent_history = await self.db.get_channel_conversation_history(
            channel_id=message.channel_id,
            limit=30,
        )

        # Build JARVIS system prompt
        base_prompt = """Eres JARVIS, el bot de este server de Discord. Grupo de amigos chilenos, todos jugadores.

Personalidad:
- Gen Z chileno. Directo, seco, un poco edgy. No das sermones ni explicas lo obvio.
- Mezclas español con inglés cuando queda natural ("that's rough", "no shot", "literally", "ngl")
- Slang chileno con moderación: "wn", "po", "ql". No lo repites en cada línea.
- Dry humor > exclamaciones. Nunca usas signos de exclamación.
- Respuestas de 1-2 líneas. Si es conversación casual, una línea está bien.
- No eres un asistente servicial. Eres el bot del grupo, con opinión propia.
- Si alguien dice algo cringe lo notas. Si alguien la caga en un juego lo sabes y lo puedes mencionar.
- Recuerdas lo que la gente te dice. Si alguien contó algo antes, puedes referenciarlo.
- No usas emojis nunca.
- Tienes memoria persistente de los jugadores. Usa el tool remember_player para guardar cosas interesantes sobre ellos.

Tienes tools para stats de partidas, rankings, voz, actividad del server, y memoria de jugadores. Úsalas cuando sea relevante."""

        # Inject player-specific notes if we have any
        player_notes = self.player_memory.get_notes_for_prompt(
            message.author_id, message.author_name
        )
        system_prompt = base_prompt + player_notes

        # Build LLM messages from persistent history
        llm_messages = []

        # Add persistent history as proper user/assistant turns
        for entry in persistent_history:
            role = entry["role"]
            if role == "user":
                llm_messages.append({
                    "role": "user",
                    "content": f"{entry['display_name']}: {entry['content']}",
                })
            else:
                llm_messages.append({
                    "role": "assistant",
                    "content": entry["content"],
                })

        # Add current message (clean mention from content)
        clean_content = message.content
        if self.gateway.client.user:
            clean_content = clean_content.replace(
                f"<@{self.gateway.client.user.id}>", ""
            ).replace(
                f"<@!{self.gateway.client.user.id}>", ""
            ).strip()

        # Build current message content — include image if present
        if message.image_url:
            current_content = [
                {
                    "type": "image",
                    "source": {"type": "url", "url": message.image_url},
                },
                {
                    "type": "text",
                    "text": f"{message.author_name}: {clean_content}" if clean_content else message.author_name,
                },
            ]
        else:
            current_content = f"{message.author_name}: {clean_content}"

        llm_messages.append({
            "role": "user",
            "content": current_content,
        })

        # Ensure alternating roles (Anthropic requires user/assistant alternation)
        # Deduplicate consecutive same-role messages by merging them
        merged_messages = []
        for msg in llm_messages:
            if merged_messages and merged_messages[-1]["role"] == msg["role"]:
                prev = merged_messages[-1]
                curr_content = msg["content"]
                # If either side is a list (vision block), normalize both to lists and extend
                if isinstance(prev["content"], list) or isinstance(curr_content, list):
                    if not isinstance(prev["content"], list):
                        prev["content"] = [{"type": "text", "text": prev["content"]}]
                    if isinstance(curr_content, list):
                        prev["content"].extend(curr_content)
                    else:
                        prev["content"].append({"type": "text", "text": curr_content})
                else:
                    prev["content"] += f"\n{curr_content}"
            else:
                merged_messages.append(dict(msg))
        llm_messages = merged_messages

        # Full messages list with system prompt handled separately for Anthropic
        messages = [{"role": "system", "content": system_prompt}] + llm_messages

        # Save the user's message to persistent history
        await self.db.save_conversation_message(
            discord_id=message.author_id,
            display_name=message.author_name,
            channel_id=message.channel_id,
            role="user",
            content=clean_content,
        )

        # Call LLM with tools
        final_text = ""
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

                # Remove system message for continuation (Anthropic handles it separately)
                continuation_messages = [
                    msg for msg in llm_messages
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
                response = await self.llm.client.messages.create(
                    model=self.llm.model,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=continuation_messages,
                    temperature=0.8,
                )

                for block in response.content:
                    if block.type == "text":
                        final_text += block.text

                await self.gateway.send(message.channel_id, final_text)
            elif text_response:
                final_text = text_response
                await self.gateway.send(message.channel_id, final_text)
            else:
                final_text = "A la orden, aunque no entendí bien qué querías wn."
                await self.gateway.send(message.channel_id, final_text)
        else:
            # Fallback to simple chat without tools (for OpenAI or other providers)
            final_text = await self.llm.chat(messages, temperature=0.8)
            await self.gateway.send(message.channel_id, final_text)

        # Save JARVIS response to persistent history (use bot's discord_id)
        if final_text:
            bot_id = str(self.gateway.client.user.id) if self.gateway.client.user else "jarvis"
            bot_name = self.gateway.client.user.display_name if self.gateway.client.user else "JARVIS"
            await self.db.save_conversation_message(
                discord_id=bot_id,
                display_name=bot_name,
                channel_id=message.channel_id,
                role="assistant",
                content=final_text,
            )
            # Prune old history to avoid bloat (keep last 50 per user)
            await self.db.prune_conversation_history(
                discord_id=message.author_id,
                channel_id=message.channel_id,
                keep_last=50,
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
