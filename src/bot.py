"""
  Interfaces discord with the ollama AI service.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
import requests

TIMEOUT = 50000
TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434/api/generate")
INTENTS = discord.Intents.default()
INTENTS.message_content = True              # Required to read message text
CLIENT = discord.Client(intents=INTENTS)

OLLAMA_API_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = "gemma3:1b-it-q4_K_M"

class HealthHandler(BaseHTTPRequestHandler):
    """ Add a handler for the healthcheck. """

    def do_GET(self):
        """ Run the logic for the health endpoints. """
        if self.path == '/healthz':
            token = os.getenv("DISCORD_TOKEN", "")
            if token:
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
    """ Run the healthcheck endpoint on port 8080. """
    server = HTTPServer(('', 8080), HealthHandler)
    server.serve_forever()

@CLIENT.event
async def on_ready():
    """ Echo who we're logged in as. """
    print(f"Logged in as {CLIENT.user}")


@CLIENT.event
async def on_message(message):
    """ Sends AI reply from message. """

    # Prevent bot from replying to itself.
    if message.author == CLIENT.user:
        return

    prompt = message.content.strip()
    user = message.author.name  # or message.author.display_name
    print(f"Received message from {user}: {prompt}")

    if message.content.startswith("!ask"):
        prompt = message.content[5:]
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": "gemma3:1b-it-q4_K_M",
            "prompt": prompt
        }, timeout=TIMEOUT)
        reply = res.json().get("response", "Error from Ollama.")
        await message.channel.send(reply)


# Start health server in a background thread
threading.Thread(target=run_health_server, daemon=True).start()
print(TOKEN)
CLIENT.run(TOKEN)
