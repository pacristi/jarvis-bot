"""Tool executor for JARVIS LLM integration."""

from typing import Any, Optional
from ..database.repository import Database
from ..gateways.base import Gateway
from ..services.match_parser import MatchParser
from ..services.roast_generator import RoastGenerator
from ..services.audio_player import AudioPlayer


class ToolExecutor:
    """Executes tool calls from the LLM."""

    def __init__(
        self,
        db: Database,
        gateway: Gateway,
        match_parser: MatchParser,
        roast_generator: RoastGenerator,
    ):
        self.db = db
        self.gateway = gateway
        self.match_parser = match_parser
        self.roast_generator = roast_generator
        self.audio_player = AudioPlayer()
        self._current_message = None  # Set by caller before execute

    async def execute(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a tool call.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result as a dictionary
        """
        if tool_name == "get_ranking":
            return await self._get_ranking(tool_input.get("game"))
        elif tool_name == "get_player_stats":
            return await self._get_player_stats(
                tool_input["player_name"], tool_input.get("game")
            )
        elif tool_name == "get_server_stats":
            return await self._get_server_stats()
        elif tool_name == "record_match":
            return await self._record_match(tool_input["image_url"])
        elif tool_name == "get_voice_stats":
            return await self._get_voice_stats(tool_input.get("player_name"))
        elif tool_name == "get_message_stats":
            return await self._get_message_stats(tool_input.get("player_name"))
        elif tool_name == "play_sound":
            return await self._play_sound(tool_input.get("sound_name", "prime"))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _play_sound(self, sound_name: str) -> dict[str, Any]:
        """Play a sound in the user's voice channel."""
        if not self._current_message:
            return {"success": False, "message": "No hay contexto de mensaje"}
        
        raw_msg = self._current_message.raw_message
        if not raw_msg or not hasattr(raw_msg, 'author'):
            return {"success": False, "message": "No puedo acceder al mensaje original"}
        
        author = raw_msg.author
        if not author.voice or not author.voice.channel:
            return {"success": False, "message": "No estás en un canal de voz"}
        
        voice_channel = author.voice.channel
        result = await self.audio_player.play_sound(sound_name, voice_channel)
        
        return {"success": True, "message": result}

    async def _get_ranking(self, game: Optional[str] = None) -> dict[str, Any]:
        """Get ranking/leaderboard."""
        rankings = await self.db.get_ranking(game_name=game, limit=10)

        if not rankings:
            return {"success": False, "message": "No matches have been recorded yet."}

        return {
            "success": True,
            "game": game,
            "rankings": [
                {
                    "position": i + 1,
                    "display_name": rank["display_name"],
                    "wins": rank["wins"],
                    "total_matches": rank["total_matches"],
                    "win_rate": (rank["wins"] / rank["total_matches"] * 100)
                    if rank["total_matches"] > 0
                    else 0,
                    "avg_position": rank["avg_position"],
                    "jaulas": rank.get("jaulas", 0),
                    "protagonistas": rank.get("protagonistas", 0),
                }
                for i, rank in enumerate(rankings)
            ],
        }

    async def _get_player_stats(
        self, player_name: str, game: Optional[str] = None
    ) -> dict[str, Any]:
        """Get stats for a specific player."""
        # Try to find player by display name or nickname
        player = await self.db.get_player_by_nickname(player_name)

        if not player:
            return {
                "success": False,
                "message": f"Player '{player_name}' not found in database.",
            }

        stats = await self.db.get_player_stats(player.id, game_name=game)

        if not stats or stats.get("total_matches", 0) == 0:
            return {
                "success": False,
                "message": f"No matches recorded for {player.display_name}"
                + (f" in {game}" if game else ""),
            }

        total_matches = stats.get("total_matches", 0)
        wins = stats.get("wins", 0)

        return {
            "success": True,
            "player_name": player.display_name,
            "game": game,
            "total_matches": total_matches,
            "wins": wins,
            "win_rate": (wins / total_matches * 100) if total_matches > 0 else 0,
            "avg_position": stats.get("avg_position", 0),
            "avg_score": stats.get("avg_score"),
            "jaulas": stats.get("jaulas", 0),
            "protagonistas": stats.get("protagonistas", 0),
        }

    async def _get_server_stats(self) -> dict[str, Any]:
        """Get overall server statistics."""
        server_stats = await self.db.get_server_stats()

        # Get top performers
        match_ranking = await self.db.get_ranking(limit=3)
        voice_ranking = await self.db.get_voice_leaderboard(limit=3)
        message_ranking = await self.db.get_message_leaderboard(limit=3)

        result = {
            "success": True,
            "total_players": server_stats.get("total_players", 0),
            "total_matches": server_stats.get("total_matches", 0),
            "total_voice_sessions": server_stats.get("total_voice_sessions", 0),
            "total_messages": server_stats.get("total_messages", 0),
        }

        if match_ranking:
            top_player = match_ranking[0]
            result["top_match_winner"] = {
                "name": top_player["display_name"],
                "wins": top_player["wins"],
                "total_matches": top_player["total_matches"],
            }

        if voice_ranking:
            top_voice = voice_ranking[0]
            result["most_vocal"] = {
                "name": top_voice["display_name"],
                "total_seconds": top_voice.get("total_seconds", 0) or 0,
                "total_sessions": top_voice["total_sessions"],
            }

        if message_ranking:
            top_msg = message_ranking[0]
            result["most_chatty"] = {
                "name": top_msg["display_name"],
                "total_messages": top_msg["total_messages"],
            }

        return result

    async def _record_match(self, image_url: str) -> dict[str, Any]:
        """Record a match from screenshot."""
        try:
            # Parse screenshot using LLM vision
            parsed = await self.match_parser.parse_screenshot(image_url)

            # For now, we'll create a match with a placeholder recorder
            # In production, this would use the actual user who triggered the tool
            recorder = await self.db.get_player_by_discord_id("system")
            if not recorder:
                recorder = await self.db.create_player("system", "JARVIS")

            # Create match record
            match = await self.db.create_match(
                game_name=parsed.game_name,
                recorded_by=recorder.id,
                screenshot_url=image_url,
            )

            # Process each player and create results
            player_results = []
            for ranking in parsed.rankings:
                player_name = ranking["player"]
                position = ranking["position"]
                score = ranking.get("score")

                # Try to find player by nickname, otherwise create new
                player = await self.db.get_player_by_nickname(player_name)
                if not player:
                    temp_discord_id = f"unknown_{player_name.lower().replace(' ', '_')}"
                    player = await self.db.create_player(temp_discord_id, player_name)
                    await self.db.add_nickname(player.id, player_name)

                # Create result
                await self.db.create_result(
                    match_id=match.id,
                    player_id=player.id,
                    position=position,
                    score=score,
                )

                player_results.append(
                    {"name": player_name, "position": position, "score": score}
                )

            return {
                "success": True,
                "match_id": match.id,
                "game_name": parsed.game_name,
                "players": player_results,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_voice_stats(
        self, player_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Get voice activity statistics."""
        if player_name:
            # Get specific player stats
            player = await self.db.get_player_by_nickname(player_name)
            if not player:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' not found in database.",
                }

            stats = await self.db.get_voice_stats(player.id)
            total_sessions = stats.get("total_sessions", 0)

            if total_sessions == 0:
                return {
                    "success": False,
                    "message": f"{player.display_name} has no voice activity recorded.",
                }

            # Get leaderboard position
            leaderboard = await self.db.get_voice_leaderboard(limit=100)
            position = None
            for i, entry in enumerate(leaderboard, 1):
                if entry["id"] == player.id:
                    position = i
                    break

            return {
                "success": True,
                "player_name": player.display_name,
                "total_sessions": total_sessions,
                "total_seconds": stats.get("total_seconds", 0) or 0,
                "avg_session_seconds": stats.get("avg_session_seconds", 0) or 0,
                "longest_session_seconds": stats.get("longest_session_seconds", 0) or 0,
                "leaderboard_position": position,
            }
        else:
            # Get leaderboard
            leaderboard = await self.db.get_voice_leaderboard(limit=10)

            if not leaderboard:
                return {"success": False, "message": "No voice activity recorded yet."}

            return {
                "success": True,
                "leaderboard": [
                    {
                        "position": i + 1,
                        "display_name": entry["display_name"],
                        "total_seconds": entry["total_seconds"] or 0,
                        "total_sessions": entry["total_sessions"],
                    }
                    for i, entry in enumerate(leaderboard)
                ],
            }

    async def _get_message_stats(
        self, player_name: Optional[str] = None
    ) -> dict[str, Any]:
        """Get message activity statistics."""
        if player_name:
            # Get specific player stats
            player = await self.db.get_player_by_nickname(player_name)
            if not player:
                return {
                    "success": False,
                    "message": f"Player '{player_name}' not found in database.",
                }

            stats = await self.db.get_message_stats(player.id)

            if stats.get("total_messages", 0) == 0:
                return {
                    "success": False,
                    "message": f"{player.display_name} has no messages recorded.",
                }

            # Get leaderboard position
            leaderboard = await self.db.get_message_leaderboard(limit=100)
            position = None
            for i, entry in enumerate(leaderboard, 1):
                if entry["id"] == player.id:
                    position = i
                    break

            return {
                "success": True,
                "player_name": player.display_name,
                "total_messages": stats.get("total_messages", 0),
                "channels_used": stats.get("channels_used", 0),
                "leaderboard_position": position,
            }
        else:
            # Get leaderboard
            leaderboard = await self.db.get_message_leaderboard(limit=10)

            if not leaderboard:
                return {
                    "success": False,
                    "message": "No message activity recorded yet.",
                }

            return {
                "success": True,
                "leaderboard": [
                    {
                        "position": i + 1,
                        "display_name": entry["display_name"],
                        "total_messages": entry["total_messages"],
                    }
                    for i, entry in enumerate(leaderboard)
                ],
            }
