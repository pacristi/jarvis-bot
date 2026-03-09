"""Player memory service - persistent notes about players."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class PlayerMemory:
    """Manages persistent memory/notes about players."""
    
    def __init__(self, memory_path: str = "player_memories.json"):
        self.memory_path = Path(memory_path)
        self.memories: dict = {}
        self._load()
    
    def _load(self) -> None:
        """Load memories from disk."""
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading player memories: {e}")
                self.memories = {}
        else:
            self.memories = {}
    
    def _save(self) -> None:
        """Save memories to disk."""
        try:
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving player memories: {e}")
    
    def get_player_notes(self, discord_id: str) -> Optional[dict]:
        """Get all notes for a player."""
        return self.memories.get(discord_id)
    
    def get_notes_for_prompt(self, discord_id: str, display_name: str) -> str:
        """Get formatted notes for injection into system prompt."""
        player_data = self.memories.get(discord_id)
        if not player_data:
            return ""
        
        notes = player_data.get("notes", [])
        apodo = player_data.get("apodo")
        
        if not notes and not apodo:
            return ""
        
        lines = [f"\n### Lo que sabes de {display_name}:"]
        if apodo:
            lines.append(f"- Apodo: {apodo}")
        for note in notes[-10:]:  # Last 10 notes max
            lines.append(f"- {note['text']}")
        
        return "\n".join(lines)
    
    def add_note(self, discord_id: str, display_name: str, note: str) -> str:
        """Add a note about a player."""
        if discord_id not in self.memories:
            self.memories[discord_id] = {
                "display_name": display_name,
                "notes": [],
                "apodo": None,
                "created_at": datetime.now().isoformat()
            }
        
        self.memories[discord_id]["notes"].append({
            "text": note,
            "added_at": datetime.now().isoformat()
        })
        self.memories[discord_id]["display_name"] = display_name  # Update name
        
        self._save()
        return f"Anotado sobre {display_name}: {note}"
    
    def set_apodo(self, discord_id: str, display_name: str, apodo: str) -> str:
        """Set a nickname/apodo for a player."""
        if discord_id not in self.memories:
            self.memories[discord_id] = {
                "display_name": display_name,
                "notes": [],
                "apodo": None,
                "created_at": datetime.now().isoformat()
            }
        
        old_apodo = self.memories[discord_id].get("apodo")
        self.memories[discord_id]["apodo"] = apodo
        self.memories[discord_id]["display_name"] = display_name
        
        self._save()
        
        if old_apodo:
            return f"Actualizado: {display_name} ahora es '{apodo}' (antes era '{old_apodo}')"
        return f"Anotado: {display_name} = '{apodo}'"
    
    def clear_notes(self, discord_id: str) -> str:
        """Clear all notes for a player (keep apodo)."""
        if discord_id in self.memories:
            name = self.memories[discord_id].get("display_name", "unknown")
            self.memories[discord_id]["notes"] = []
            self._save()
            return f"Borradas las notas de {name}"
        return "No tenía notas de ese usuario"
    
    def get_all_players_summary(self) -> str:
        """Get a summary of all remembered players."""
        if not self.memories:
            return "No tengo notas de nadie todavía"
        
        lines = ["**Jugadores en mi memoria:**"]
        for discord_id, data in self.memories.items():
            name = data.get("display_name", "???")
            apodo = data.get("apodo", "")
            note_count = len(data.get("notes", []))
            apodo_str = f" ({apodo})" if apodo else ""
            lines.append(f"- {name}{apodo_str}: {note_count} notas")
        
        return "\n".join(lines)
