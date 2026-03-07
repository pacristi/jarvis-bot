"""Audio player service for Discord voice channels."""

import asyncio
import discord
import os
from pathlib import Path


FFMPEG_OPTIONS = {
    'options': '-vn'
}

# Sound library - local files
SOUNDS_DIR = Path(__file__).parent.parent.parent / "sounds"
SOUNDS = {
    'prime': SOUNDS_DIR / "prime.mp3",  # Welcome to the Jungle
}


class AudioPlayer:
    """Handles playing audio in Discord voice channels."""
    
    def __init__(self):
        self.voice_client = None
    
    async def play_sound(self, sound_name: str, voice_channel: discord.VoiceChannel) -> str:
        """
        Play a sound in the specified voice channel.
        
        Args:
            sound_name: Name of the sound to play (e.g., 'prime')
            voice_channel: Discord voice channel to join
            
        Returns:
            Status message
        """
        if sound_name.lower() not in SOUNDS:
            return f"No conozco ese sonido. Disponibles: {', '.join(SOUNDS.keys())}"
        
        audio_path = SOUNDS[sound_name.lower()]
        
        if not audio_path.exists():
            return f"Archivo de audio no encontrado: {audio_path}"
        
        try:
            # Connect to voice channel
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.disconnect()
            
            self.voice_client = await voice_channel.connect()
            
            # Play local audio file
            source = discord.FFmpegPCMAudio(str(audio_path), **FFMPEG_OPTIONS)
            self.voice_client.play(source)
            
            # Wait for it to finish (max 5 min)
            timeout = 300
            while self.voice_client.is_playing() and timeout > 0:
                await asyncio.sleep(1)
                timeout -= 1
            
            # Disconnect
            await self.voice_client.disconnect()
            self.voice_client = None
            
            return "🎸 Prime activado"
            
        except Exception as e:
            if self.voice_client:
                try:
                    await self.voice_client.disconnect()
                except:
                    pass
                self.voice_client = None
            return f"Error: {str(e)}"
