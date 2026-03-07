"""Audio player service for Discord voice channels."""

import asyncio
import discord
import yt_dlp
import os
from pathlib import Path


# YouTube DL options
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# Sound library
SOUNDS = {
    'prime': 'https://www.youtube.com/watch?v=9erLsEHAZRI',  # Welcome to the Jungle
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
        
        url = SOUNDS[sound_name.lower()]
        
        try:
            # Connect to voice channel
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.disconnect()
            
            self.voice_client = await voice_channel.connect()
            
            # Get audio URL from YouTube
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
            
            # Play audio
            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            self.voice_client.play(source)
            
            # Wait for it to finish (max 60 seconds for a clip)
            timeout = 60
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
