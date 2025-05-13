"""
  Interfaces discord with the ollama AI service.
"""
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import aiohttp
import discord
import requests

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b-it-q4_K_M")

INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.message_content = True

CLIENT = discord.Client(intents=INTENTS)

# 🩺 Health server to support Kubernetes probes
class HealthHandler(BaseHTTPRequestHandler):
    """
      Handles the health endpoints.
    """
    def do_GET(self):
        """
          Handle GET requests.
        """
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
    """
      Runs the listener for the health server.
    """
    server = HTTPServer(('', 8080), HealthHandler)
    server.serve_forever()


@CLIENT.event
async def on_message(message):
    """
      🎤 Respond to messages directed to the bot.
    """
    # Ignore messages from the bot itself
    if message.author == CLIENT.user:
        return

    is_mentioned = CLIENT.user in message.mentions
    is_ask_command = message.content.startswith("!ask")

    if not (is_mentioned or is_ask_command):
        return

    prompt = message.content
    if is_ask_command:
        prompt = prompt[len("!ask"):].strip()
    elif is_mentioned:
        prompt = prompt.replace(f"<@{CLIENT.user.id}>", "").strip()

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
                if reply:
                    await message.channel.send(reply)
                else:
                    await message.channel.send("🤔 Got an empty response from Ollama.")
    except requests.exceptions.RequestException as error_message:
        logging.exception("❌ Error contacting Ollama: %s", error_message)
        await message.channel.send("🚨 Failed to contact Ollama service.")
    except Exception as error_message:
        logging.exception("❌ Unexpected error: %s", error_message)
        await message.channel.send("⚠️ An unexpected error occurred.")


@CLIENT.event
async def on_ready():
    """
      Print when we're ready.
    """
    print(f"✅ Logged in as {CLIENT.user}")

# Start health server in background thread
threading.Thread(target=run_health_server, daemon=True).start()

# Run bot
if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN environment variable not set.")
else:
    print("Starting BOT")
    CLIENT.run(DISCORD_TOKEN)
