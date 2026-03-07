"""Database repository for JARVIS bot using aiosqlite."""

import aiosqlite
from datetime import datetime
from typing import Optional
from pathlib import Path

from .models import (
    Player,
    PlayerNickname,
    LinkedAccount,
    Match,
    Result,
    VoiceSession,
    MessageActivity,
)


# SQL schema
SCHEMA = """
-- Jugadores del server
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Nicknames que usa en juegos (para matching de screenshots)
CREATE TABLE IF NOT EXISTS player_nicknames (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    nickname TEXT NOT NULL,
    UNIQUE(player_id, nickname)
);

-- Cuentas externas (Riot, Steam, etc.)
CREATE TABLE IF NOT EXISTS linked_accounts (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    platform TEXT NOT NULL,
    game_id TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, platform)
);

-- Partidas (cualquier juego)
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    game_name TEXT NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    screenshot_url TEXT,
    recorded_by INTEGER REFERENCES players(id)
);

-- Resultados por partida
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    player_id INTEGER REFERENCES players(id),
    position INTEGER NOT NULL,
    score INTEGER,
    extra_data TEXT,
    UNIQUE(match_id, player_id)
);

-- Sesiones de voz (voice channels)
CREATE TABLE IF NOT EXISTS voice_sessions (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    channel_id TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    joined_at TIMESTAMP NOT NULL,
    left_at TIMESTAMP,
    duration_seconds INTEGER
);

-- Actividad de mensajes
CREATE TABLE IF NOT EXISTS message_activity (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    channel_id TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    message_count INTEGER DEFAULT 1,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    """SQLite database interface using aiosqlite."""

    def __init__(self, db_path: str = "jarvis.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to the database and initialize schema."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()

    # Players
    async def create_player(self, discord_id: str, display_name: str) -> Player:
        """Create a new player."""
        cursor = await self._conn.execute(
            "INSERT INTO players (discord_id, display_name) VALUES (?, ?)",
            (discord_id, display_name),
        )
        await self._conn.commit()
        return Player(
            id=cursor.lastrowid,
            discord_id=discord_id,
            display_name=display_name,
            created_at=datetime.now(),
        )

    async def get_player_by_discord_id(self, discord_id: str) -> Optional[Player]:
        """Get player by Discord ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM players WHERE discord_id = ?", (discord_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Player(**dict(row))
        return None

    async def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Player(**dict(row))
        return None

    # Player Nicknames
    async def add_nickname(self, player_id: int, nickname: str) -> PlayerNickname:
        """Add a nickname for a player."""
        cursor = await self._conn.execute(
            "INSERT OR IGNORE INTO player_nicknames (player_id, nickname) VALUES (?, ?)",
            (player_id, nickname),
        )
        await self._conn.commit()
        return PlayerNickname(
            id=cursor.lastrowid, player_id=player_id, nickname=nickname
        )

    async def get_player_by_nickname(self, nickname: str) -> Optional[Player]:
        """Get player by nickname."""
        cursor = await self._conn.execute(
            """
            SELECT p.* FROM players p
            JOIN player_nicknames pn ON p.id = pn.player_id
            WHERE pn.nickname = ?
            """,
            (nickname,),
        )
        row = await cursor.fetchone()
        if row:
            return Player(**dict(row))
        return None

    # Matches
    async def create_match(
        self, game_name: str, recorded_by: int, screenshot_url: Optional[str] = None
    ) -> Match:
        """Create a new match."""
        cursor = await self._conn.execute(
            "INSERT INTO matches (game_name, recorded_by, screenshot_url) VALUES (?, ?, ?)",
            (game_name, recorded_by, screenshot_url),
        )
        await self._conn.commit()
        return Match(
            id=cursor.lastrowid,
            game_name=game_name,
            recorded_by=recorded_by,
            screenshot_url=screenshot_url,
            played_at=datetime.now(),
        )

    async def get_match(self, match_id: int) -> Optional[Match]:
        """Get match by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM matches WHERE id = ?", (match_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Match(**dict(row))
        return None

    async def get_recent_matches(self, limit: int = 10) -> list[Match]:
        """Get recent matches."""
        cursor = await self._conn.execute(
            "SELECT * FROM matches ORDER BY played_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [Match(**dict(row)) for row in rows]

    # Results
    async def create_result(
        self,
        match_id: int,
        player_id: int,
        position: int,
        score: Optional[int] = None,
        extra_data: Optional[str] = None,
    ) -> Result:
        """Create a result for a match."""
        cursor = await self._conn.execute(
            """
            INSERT INTO results (match_id, player_id, position, score, extra_data)
            VALUES (?, ?, ?, ?, ?)
            """,
            (match_id, player_id, position, score, extra_data),
        )
        await self._conn.commit()
        return Result(
            id=cursor.lastrowid,
            match_id=match_id,
            player_id=player_id,
            position=position,
            score=score,
            extra_data=extra_data,
        )

    async def get_results_for_match(self, match_id: int) -> list[Result]:
        """Get all results for a match."""
        cursor = await self._conn.execute(
            "SELECT * FROM results WHERE match_id = ? ORDER BY position", (match_id,)
        )
        rows = await cursor.fetchall()
        return [Result(**dict(row)) for row in rows]

    async def get_player_stats(
        self, player_id: int, game_name: Optional[str] = None
    ) -> dict:
        """Get aggregated stats for a player."""
        if game_name:
            cursor = await self._conn.execute(
                """
                SELECT 
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN position = 1 THEN 1 ELSE 0 END) as wins,
                    AVG(position) as avg_position,
                    AVG(score) as avg_score
                FROM results r
                JOIN matches m ON r.match_id = m.id
                WHERE r.player_id = ? AND m.game_name = ?
                """,
                (player_id, game_name),
            )
        else:
            cursor = await self._conn.execute(
                """
                SELECT 
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN position = 1 THEN 1 ELSE 0 END) as wins,
                    AVG(position) as avg_position,
                    AVG(score) as avg_score
                FROM results
                WHERE player_id = ?
                """,
                (player_id,),
            )
        row = await cursor.fetchone()
        result = dict(row) if row else {}

        # Count jaulas and protagonistas from extra_data
        if result:
            import json

            extra_cursor = await self._conn.execute(
                """
                SELECT extra_data 
                FROM results r
                """
                + (
                    "JOIN matches m ON r.match_id = m.id WHERE r.player_id = ? AND m.game_name = ?"
                    if game_name
                    else "WHERE player_id = ?"
                ),
                (player_id, game_name) if game_name else (player_id,),
            )
            extra_rows = await extra_cursor.fetchall()

            jaulas_count = 0
            protagonista_count = 0

            for ed_row in extra_rows:
                if ed_row["extra_data"]:
                    try:
                        extra_data = json.loads(ed_row["extra_data"])
                        if extra_data.get("jaula"):
                            jaulas_count += 1
                        if extra_data.get("protagonista"):
                            protagonista_count += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

            result["jaulas"] = jaulas_count
            result["protagonistas"] = protagonista_count

        return result

    async def get_ranking(
        self, game_name: Optional[str] = None, limit: int = 10
    ) -> list[dict]:
        """Get player ranking by wins."""
        if game_name:
            cursor = await self._conn.execute(
                """
                SELECT 
                    p.id,
                    p.display_name,
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as wins,
                    AVG(r.position) as avg_position,
                    r.extra_data
                FROM players p
                JOIN results r ON p.id = r.player_id
                JOIN matches m ON r.match_id = m.id
                WHERE m.game_name = ?
                GROUP BY p.id
                ORDER BY wins DESC, avg_position ASC
                LIMIT ?
                """,
                (game_name, limit),
            )
        else:
            cursor = await self._conn.execute(
                """
                SELECT 
                    p.id,
                    p.display_name,
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as wins,
                    AVG(r.position) as avg_position,
                    r.extra_data
                FROM players p
                JOIN results r ON p.id = r.player_id
                GROUP BY p.id
                ORDER BY wins DESC, avg_position ASC
                LIMIT ?
                """,
                (limit,),
            )
        rows = await cursor.fetchall()

        # Process extra_data to count jaulas and protagonistas
        import json

        result = []
        for row in rows:
            row_dict = dict(row)

            # Get all extra_data for this player to count jaulas and protagonistas
            player_cursor = await self._conn.execute(
                """
                SELECT extra_data 
                FROM results 
                WHERE player_id = ?
                """
                + (
                    " AND match_id IN (SELECT id FROM matches WHERE game_name = ?)"
                    if game_name
                    else ""
                ),
                (row_dict["id"], game_name) if game_name else (row_dict["id"],),
            )
            extra_data_rows = await player_cursor.fetchall()

            jaulas_count = 0
            protagonista_count = 0

            for ed_row in extra_data_rows:
                if ed_row["extra_data"]:
                    try:
                        extra_data = json.loads(ed_row["extra_data"])
                        if extra_data.get("jaula"):
                            jaulas_count += 1
                        if extra_data.get("protagonista"):
                            protagonista_count += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

            row_dict["jaulas"] = jaulas_count
            row_dict["protagonistas"] = protagonista_count
            # Remove extra_data from final result
            row_dict.pop("extra_data", None)
            result.append(row_dict)

        return result

    # Voice Sessions
    async def start_voice_session(
        self, player_id: int, channel_id: str, channel_name: str
    ) -> VoiceSession:
        """Start a voice session for a player."""
        cursor = await self._conn.execute(
            """
            INSERT INTO voice_sessions (player_id, channel_id, channel_name, joined_at)
            VALUES (?, ?, ?, ?)
            """,
            (player_id, channel_id, channel_name, datetime.now()),
        )
        await self._conn.commit()
        return VoiceSession(
            id=cursor.lastrowid,
            player_id=player_id,
            channel_id=channel_id,
            channel_name=channel_name,
            joined_at=datetime.now(),
        )

    async def end_voice_session(self, session_id: int) -> Optional[VoiceSession]:
        """End a voice session and calculate duration."""
        # Get the session
        cursor = await self._conn.execute(
            "SELECT * FROM voice_sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        session_dict = dict(row)
        joined_at = datetime.fromisoformat(session_dict["joined_at"])
        left_at = datetime.now()
        duration = int((left_at - joined_at).total_seconds())

        # Update the session
        await self._conn.execute(
            """
            UPDATE voice_sessions
            SET left_at = ?, duration_seconds = ?
            WHERE id = ?
            """,
            (left_at, duration, session_id),
        )
        await self._conn.commit()

        return VoiceSession(**session_dict, left_at=left_at, duration_seconds=duration)

    async def get_active_voice_session(
        self, player_id: int, channel_id: str
    ) -> Optional[VoiceSession]:
        """Get active voice session for a player in a channel."""
        cursor = await self._conn.execute(
            """
            SELECT * FROM voice_sessions
            WHERE player_id = ? AND channel_id = ? AND left_at IS NULL
            ORDER BY joined_at DESC
            LIMIT 1
            """,
            (player_id, channel_id),
        )
        row = await cursor.fetchone()
        if row:
            return VoiceSession(**dict(row))
        return None

    async def get_voice_stats(self, player_id: int) -> dict:
        """Get voice activity stats for a player."""
        cursor = await self._conn.execute(
            """
            SELECT
                COUNT(*) as total_sessions,
                SUM(duration_seconds) as total_seconds,
                AVG(duration_seconds) as avg_session_seconds,
                MAX(duration_seconds) as longest_session_seconds
            FROM voice_sessions
            WHERE player_id = ? AND left_at IS NOT NULL
            """,
            (player_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}

    async def get_voice_leaderboard(self, limit: int = 10) -> list[dict]:
        """Get voice time leaderboard."""
        cursor = await self._conn.execute(
            """
            SELECT
                p.id,
                p.display_name,
                COUNT(*) as total_sessions,
                SUM(vs.duration_seconds) as total_seconds,
                AVG(vs.duration_seconds) as avg_session_seconds
            FROM players p
            JOIN voice_sessions vs ON p.id = vs.player_id
            WHERE vs.left_at IS NOT NULL
            GROUP BY p.id
            ORDER BY total_seconds DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # Message Activity
    async def record_message(
        self, player_id: int, channel_id: str, channel_name: str
    ) -> MessageActivity:
        """Record a message from a player."""
        cursor = await self._conn.execute(
            """
            INSERT INTO message_activity (player_id, channel_id, channel_name, message_count)
            VALUES (?, ?, ?, 1)
            """,
            (player_id, channel_id, channel_name),
        )
        await self._conn.commit()
        return MessageActivity(
            id=cursor.lastrowid,
            player_id=player_id,
            channel_id=channel_id,
            channel_name=channel_name,
            message_count=1,
            recorded_at=datetime.now(),
        )

    async def get_message_stats(self, player_id: int) -> dict:
        """Get message activity stats for a player."""
        cursor = await self._conn.execute(
            """
            SELECT
                COUNT(*) as total_messages,
                COUNT(DISTINCT channel_id) as channels_used
            FROM message_activity
            WHERE player_id = ?
            """,
            (player_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}

    async def get_message_leaderboard(self, limit: int = 10) -> list[dict]:
        """Get message count leaderboard."""
        cursor = await self._conn.execute(
            """
            SELECT
                p.id,
                p.display_name,
                COUNT(*) as total_messages,
                COUNT(DISTINCT ma.channel_id) as channels_used
            FROM players p
            JOIN message_activity ma ON p.id = ma.player_id
            GROUP BY p.id
            ORDER BY total_messages DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_server_stats(self) -> dict:
        """Get overall server statistics."""
        cursor = await self._conn.execute(
            """
            SELECT
                COUNT(DISTINCT p.id) as total_players,
                COUNT(DISTINCT m.id) as total_matches,
                COUNT(DISTINCT vs.id) as total_voice_sessions,
                COUNT(DISTINCT ma.id) as total_messages
            FROM players p
            LEFT JOIN matches m ON p.id = m.recorded_by
            LEFT JOIN voice_sessions vs ON p.id = vs.player_id
            LEFT JOIN message_activity ma ON p.id = ma.player_id
            """
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}
