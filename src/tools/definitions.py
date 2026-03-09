"""Tool definitions for JARVIS LLM integration using Anthropic format."""

# Anthropic tool format
TOOLS = [
    {
        "name": "get_ranking",
        "description": "Get the current ranking/leaderboard for matches. Can filter by specific game or show overall ranking. Returns list of top players with their win counts, total matches, win rates, and average positions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game": {
                    "type": "string",
                    "description": "Optional: Filter by specific game name (e.g., 'Mario Kart', 'Super Smash Bros'). If not provided, shows overall ranking across all games.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_player_stats",
        "description": "Get detailed statistics for a specific player. Returns match stats including total matches played, wins, average position, average score, and other performance metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "The name of the player to get stats for. Can be their display name or nickname.",
                },
                "game": {
                    "type": "string",
                    "description": "Optional: Filter stats by specific game name. If not provided, shows stats across all games.",
                },
            },
            "required": ["player_name"],
        },
    },
    {
        "name": "get_server_stats",
        "description": "Get overall server statistics including total players tracked, total matches recorded, voice sessions, messages sent, and top performers in each category.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "record_match",
        "description": "Register a match from a screenshot. Analyzes the image using vision AI to extract player rankings and scores, then records them in the database. Use this when users share match result screenshots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "The URL of the screenshot image showing match results.",
                }
            },
            "required": ["image_url"],
        },
    },
    {
        "name": "get_voice_stats",
        "description": "Get voice channel activity statistics. Can show individual player stats (total sessions, time spent, average session duration, longest session) or the leaderboard of most active voice users.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "Optional: Name of the player to get voice stats for. If not provided, returns the voice leaderboard of top users.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_message_stats",
        "description": "Get message activity statistics. Shows individual player message counts, channels they're active in, and their ranking compared to other users.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "Optional: Name of the player to get message stats for. If not provided, returns the message leaderboard of most active users.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "remember_player",
        "description": "Save a note or observation about a player for future reference. Use this to remember things like: gaming habits, excuses they make, funny moments, their mains in games, inside jokes, etc. This helps you roast them better later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "Name of the player to save a note about.",
                },
                "note": {
                    "type": "string",
                    "description": "The observation or note to remember. Be concise but memorable.",
                },
            },
            "required": ["player_name", "note"],
        },
    },
    {
        "name": "set_player_apodo",
        "description": "Set or update a nickname/apodo for a player. Use when someone earns a new nickname through their actions or you want to call them something specific.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "Name of the player.",
                },
                "apodo": {
                    "type": "string",
                    "description": "The nickname/apodo to assign.",
                },
            },
            "required": ["player_name", "apodo"],
        },
    },
    {
        "name": "get_player_memory",
        "description": "Get all your saved notes and memories about players. Use to remember what you know about someone or to see all players you have notes on.",
        "input_schema": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "Optional: Name of a specific player. If not provided, returns summary of all players.",
                },
            },
            "required": [],
        },
    },
]
