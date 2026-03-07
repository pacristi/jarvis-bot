"""Service for generating toxic roasts in JARVIS style."""

from typing import Optional

from ..llm.base import LLMProvider


JARVIS_SYSTEM_PROMPT = """Eres JARVIS, un bot de Discord para un grupo de amigos chilenos que trackea stats de juegos.

Tu personalidad:
- Sarcástico pero amigable, como un amigo que te webea
- Usas español chileno casual (pero no exagerado)
- Tiras comentarios cortos y al grano
- Puedes ser un poco tóxico pero siempre con cariño
- Usas datos reales para hacer los roasts más efectivos

Ejemplos de tu estilo:
- "Bro, 4 últimos lugares seguidos. ¿Estás bien en casa?"
- "47 horas en Discord este mes y sigues siendo malo. Dedication."
- "Wena. ¿Qué necesitas? Porque ayuda en los juegos claramente no."
- "Los números no mienten, y los tuyos dan penita."

Reglas:
- Respuestas cortas (1-2 oraciones)
- Nada de "Señor" ni formalidades — háblales como a amigos
- Usa humor chileno cuando calce
- Si no hay stats, igual tira algo ingenioso
- SIEMPRE en español"""


class RoastGenerator:
    """Generate JARVIS-style roasts based on match results and player stats."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_match_roast(
        self,
        player_name: str,
        position: int,
        total_players: int,
        recent_stats: Optional[dict] = None,
        discord_stats: Optional[dict] = None,
    ) -> str:
        """
        Generate a roast comment for a player after a match.

        Args:
            player_name: The player's name
            position: Their position in this match (1 = first, etc.)
            total_players: Total number of players in the match
            recent_stats: Optional dict with stats like consecutive_losses, avg_position, etc.
            discord_stats: Optional dict with voice_hours, message_count, etc.

        Returns:
            A JARVIS-style roast comment
        """
        context = f"""Player: {player_name}
Match result: Position {position} out of {total_players}"""

        if recent_stats:
            context += f"\nMatch stats: {recent_stats}"

        if discord_stats:
            context += f"\nDiscord activity: {discord_stats}"

        prompt = f"""{context}

Generate a single JARVIS-style comment about this performance. Be witty and sarcastic, but ultimately good-natured.
If Discord stats are provided, you may reference their time spent talking vs. their game performance."""

        messages = [
            {"role": "system", "content": JARVIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        return await self.llm.chat(messages, temperature=0.8)

    async def generate_ranking_roast(
        self,
        player_name: str,
        rank: int,
        stats: dict,
        discord_stats: Optional[dict] = None,
    ) -> str:
        """
        Generate a roast for a player's overall ranking.

        Args:
            player_name: The player's name
            rank: Their rank in the leaderboard
            stats: Dict with total_matches, wins, avg_position, etc.
            discord_stats: Optional dict with voice_hours, message_count, etc.

        Returns:
            A JARVIS-style roast comment
        """
        prompt = f"""Player: {player_name}
Rank: #{rank}
Match stats: {stats}"""

        if discord_stats:
            prompt += f"\nDiscord activity: {discord_stats}"

        prompt += """

Generate a JARVIS-style comment about their overall performance.
If Discord stats show high activity but poor game performance, feel free to point out the irony."""

        messages = [
            {"role": "system", "content": JARVIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        return await self.llm.chat(messages, temperature=0.8)

    async def generate_greeting(self, player_name: str) -> str:
        """
        Generate a JARVIS-style greeting when mentioned.

        Args:
            player_name: The name of the person who mentioned JARVIS

        Returns:
            A witty JARVIS greeting
        """
        prompt = f"""{player_name} just greeted or mentioned you. Generate a brief, witty JARVIS-style greeting.
Be polite but slightly condescending, as if you were interrupted from very important calculations.
Keep it to 1-2 sentences max."""

        messages = [
            {"role": "system", "content": JARVIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        return await self.llm.chat(messages, temperature=0.9)

    async def generate_contextual_response(
        self, player_name: str, current_message: str, conversation_history: str
    ) -> str:
        """
        Generate a contextual JARVIS response based on conversation history.

        Args:
            player_name: The name of the person who mentioned JARVIS
            current_message: The current message that mentioned JARVIS
            conversation_history: Recent conversation history formatted for context

        Returns:
            A contextual JARVIS response
        """
        prompt = f"""{player_name} mentioned you in this message: "{current_message}"

{conversation_history}

Based on the recent conversation context, generate a natural JARVIS-style response.
- Reference the conversation when relevant
- Keep it brief and natural (1-3 sentences)
- Be helpful if they're asking something, sarcastic if they're just chatting
- Use the context to make your response more relevant"""

        messages = [
            {"role": "system", "content": JARVIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        return await self.llm.chat(messages, temperature=0.8)
