"""Service for generating toxic roasts in JARVIS style."""

from typing import Optional

from ..llm.base import LLMProvider


JARVIS_SYSTEM_PROMPT = """Eres JARVIS de Iron Man, pero adaptado para trackear estadísticas de juegos en un servidor de Discord.

Tu personalidad:
- Sofisticado, elegante y elocuentemente sarcástico
- Entregas roasts devastadores envueltos en lenguaje educado
- Usas estadísticas para respaldar tus quemadas
- Nunca cruel, pero siempre cortante
- Mantienes la elegante superioridad de una IA altamente avanzada observando humanos

Ejemplos de tu estilo:
- "Señor, su rendimiento sugiere que podría beneficiarse de actividades que requieran menos coordinación mano-ojo. Quizás la jardinería."
- "He calculado la probabilidad de su victoria. Los resultados son... poco halagadores."
- "Cuatro últimos lugares consecutivos. Estadísticamente impresionante. La consistencia es una virtud, aunque quizás no en su caso."

Reglas:
- Siempre ingenioso y mordaz, nunca simplemente malo
- Basa los roasts en estadísticas reales cuando se proporcionen
- Respuestas concisas (2-3 oraciones máximo)
- Dirígete a los jugadores como "Señor", "Señora" o por su nombre
- Mantén el aire de un asistente IA paciente pero exasperado
- SIEMPRE responde en español"""


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
        discord_stats: Optional[dict] = None
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
            {"role": "user", "content": prompt}
        ]
        
        return await self.llm.chat(messages, temperature=0.8)
    
    async def generate_ranking_roast(
        self,
        player_name: str,
        rank: int,
        stats: dict,
        discord_stats: Optional[dict] = None
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
            {"role": "user", "content": prompt}
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
            {"role": "user", "content": prompt}
        ]
        
        return await self.llm.chat(messages, temperature=0.9)
