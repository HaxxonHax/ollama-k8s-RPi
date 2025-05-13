"""
  Interfaces discord with the ollama AI service.
"""

import os
import discord
import requests

TIMEOUT = 50000
TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

INTENTS = discord.Intents.default()
CLIENT = discord.Client(intents=INTENTS)


@CLIENT.event
async def on_message(message):
    """ Sends AI reply from message. """
    if message.author == CLIENT.user:
        return

    if message.content.startswith("!ask"):
        prompt = message.content[5:]
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": "gemma3:1b-it-q4_K_M",
            "prompt": prompt
        }, timeout=TIMEOUT)
        reply = res.json().get("response", "Error from Ollama.")
        await message.channel.send(reply)

CLIENT.run(TOKEN)
