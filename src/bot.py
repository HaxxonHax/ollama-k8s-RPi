"""
  Interfaces discord with the ollama AI service.
"""
import aiohttp
import os
import discord
import requests
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b-it-q4_K_M")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# 🩺 Health server to support Kubernetes probes
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            if DISCORD_TOKEN:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Missing DISCORD_TOKEN")
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    server = HTTPServer(('', 8080), HealthHandler)
    server.serve_forever()

# 🎤 Respond to messages directed to the bot
@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    is_mentioned = client.user in message.mentions
    is_ask_command = message.content.startswith("!ask")

    if not (is_mentioned or is_ask_command):
        return

    prompt = message.content
    if is_ask_command:
        prompt = prompt[len("!ask"):].strip()
    elif is_mentioned:
        prompt = prompt.replace(f"<@{client.user.id}>", "").strip()

    if not prompt:
        await message.channel.send("Please include a prompt!")
        return

    print(f"[{message.author}] asked: {prompt}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                data = await resp.json()
                reply = data.get("response", "🤖 Something went wrong.")
    except Exception as e:
        print(f"Error during Ollama request: {e}")
        reply = "🚨 Failed to contact Ollama service."

    await message.channel.send(reply)


@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

# Start health server in background thread
threading.Thread(target=run_health_server, daemon=True).start()

# Run bot
if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN environment variable not set.")
else:
    client.run(DISCORD_TOKEN)

