"""Command handler for /partido - register a match from screenshot."""

from typing import Optional

from ..database.repository import Database
from ..gateways.base import Gateway, Message
from ..services.match_parser import MatchParser
from ..services.roast_generator import RoastGenerator


class PartidoCommand:
    """Handle /partido command to register matches from screenshots."""
    
    def __init__(
        self,
        db: Database,
        gateway: Gateway,
        match_parser: MatchParser,
        roast_generator: RoastGenerator
    ):
        self.db = db
        self.gateway = gateway
        self.match_parser = match_parser
        self.roast_generator = roast_generator
    
    async def handle(self, message: Message) -> None:
        """
        Handle /partido command.
        
        Expected usage: User sends '/partido' with an image attachment
        """
        # Check if image is attached
        if not message.image_url:
            await self.gateway.send(
                message.channel_id,
                "Sir, I require a screenshot to analyze. Please attach an image of the match results."
            )
            return
        
        # Send processing message
        await self.gateway.send(
            message.channel_id,
            "Processing your... 'performance'. One moment."
        )
        
        try:
            # Parse screenshot using LLM vision
            parsed = await self.match_parser.parse_screenshot(message.image_url)
            
            # Get or create recorder player
            recorder = await self.db.get_player_by_discord_id(message.author_id)
            if not recorder:
                recorder = await self.db.create_player(message.author_id, message.author_name)
            
            # Create match record
            match = await self.db.create_match(
                game_name=parsed.game_name,
                recorded_by=recorder.id,
                screenshot_url=message.image_url
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
                    # Create a placeholder Discord ID based on nickname
                    # In a real scenario, the bot would need to link these
                    temp_discord_id = f"unknown_{player_name.lower().replace(' ', '_')}"
                    player = await self.db.create_player(temp_discord_id, player_name)
                    await self.db.add_nickname(player.id, player_name)
                
                # Create result
                await self.db.create_result(
                    match_id=match.id,
                    player_id=player.id,
                    position=position,
                    score=score
                )
                
                player_results.append({
                    "name": player_name,
                    "position": position,
                    "score": score,
                    "player_id": player.id
                })
            
            # Format confirmation message
            rankings_text = "\n".join([
                f"{r['position']}° {r['name']}" + (f" ({r['score']} pts)" if r['score'] else "")
                for r in player_results
            ])
            
            confirmation = f"""Match registered: **{parsed.game_name}**

{rankings_text}

Match ID: {match.id}"""
            
            await self.gateway.send(message.channel_id, confirmation)
            
            # Generate a roast for the last place player
            if player_results:
                last_place = player_results[-1]
                
                # Get recent stats for context
                stats = await self.db.get_player_stats(last_place["player_id"], parsed.game_name)
                
                roast = await self.roast_generator.generate_match_roast(
                    player_name=last_place["name"],
                    position=last_place["position"],
                    total_players=len(player_results),
                    recent_stats=stats
                )
                
                await self.gateway.send(message.channel_id, roast)
        
        except Exception as e:
            await self.gateway.send(
                message.channel_id,
                f"I encountered a processing error: {str(e)}\n\nPerhaps the screenshot quality is... inadequate?"
            )
