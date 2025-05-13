"""
  Interfaces discord with the ollama AI service.
"""
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import asyncio
import json
import aiohttp
import discord
import replicate

MAX_DISCORD_LENGTH = 4000
MAX_DISCORD_CHUNK = 1900
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b-it-q4_K_M")

INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.message_content = True

CLIENT = discord.Client(intents=INTENTS)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


IMAGE_TRIGGER_KEYWORDS = ["create an image", "draw", "picture"]

def is_image_prompt(prompt: str) -> bool:
    """
      Detects if the prompt is asking to create an image.
    """
    lowered = prompt.lower()
    return any(keyword in lowered for keyword in IMAGE_TRIGGER_KEYWORDS)


async def generate_image_with_replicate(prompt: str) -> str:
    """
      Offloads image generation to Replicate.
    """
    if not REPLICATE_API_TOKEN:
        raise Exception("Replicate API token not set")

    replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

    output = replicate_client.run(
        "stability-ai/stable-diffusion:db21e45e23b7b99f9a4d88a35566c4d1b3275bba2099f3a60bb65c6d60c30546",
        input={"prompt": prompt}
    )

    # Output is a URL to the image
    return output[0]  # first image URL


def chunk_message(text, max_len=MAX_DISCORD_CHUNK):
    """
      Break up a message into multiple chunks before sending to not exceed limit.
    """
    lines = text.splitlines()
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_len:
            chunks.append(current)
            current = line
        else:
            current += ("\n" if current else "") + line

    if current:
        chunks.append(current)

    return chunks


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
    if message.author == CLIENT.user:
        return

    if CLIENT.user.mentioned_in(message) or message.content.startswith("!ask"):
        prompt = message.content.replace(f"<@{CLIENT.user.id}>", "").replace("!ask", "").strip()
        if not prompt:
            await message.channel.send("📝 Please include a prompt after mentioning me or using `!ask`.")
            return

        if is_image_prompt(prompt):
            try:
                logger.info("[DEBUG] Generating an image, one moment...")
                await message.channel.send("🎨 Generating an image, one moment...")
                # Optional: ask gemma3 to enrich the description
                enriched_prompt = await generate_response_with_ollama(prompt)  # your existing logic
                image_url = await generate_image_with_replicate(enriched_prompt)
                await message.channel.send(image_url)
            except Exception as error_message:
                logger.error("Image generation error: %s", error_message)
                await message.channel.send("❌ Failed to generate image.")
            return
        try:
            logger.info("[DEBUG] Sending prompt: %s", prompt)
            timeout = aiohttp.ClientTimeout(total=600)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                async with session.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 800  # this limits tokens (400 => ~300–500 words)
                        }
                    },
                ) as resp:
                    if resp.status != 200:
                        await message.channel.send("🚨 Ollama returned a non-200 response.")
                        return

                    response_text = ""
                    async for line in resp.content:
                        decoded = line.decode("utf-8").strip()
                        if decoded:
                            try:
                                data = json.loads(decoded)
                                response_text += data.get("response", "")
                            except Exception as parse_err:
                                logger.warning("[WARN] Could not parse line: %s", decoded)
                                logger.warning(parse_err)

                    final_response = response_text.strip()
                    logger.info("[DEBUG] Response: %s", final_response)

                    if final_response:
                        chunks = chunk_message(final_response)
                        for chunk in chunks:
                            await message.channel.send(chunk)
                    else:
                        await message.channel.send("🤔 Got an empty response from Ollama.")

        except asyncio.TimeoutError:
            logging.exception("⏰ Timed out while waiting for Ollama.")
            await message.channel.send("⏰ Ollama took too long to respond.")
        except Exception:
            logging.exception("❌ Unexpected error")
            await message.channel.send("⚠️ An unexpected error occurred.")


@CLIENT.event
async def on_ready():
    """
      Print when we're ready.
    """
    logger.info("✅ Logged in as %s", CLIENT.user)

# Start health server in background thread
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
threading.Thread(target=run_health_server, daemon=True).start()

# Run bot
if not DISCORD_TOKEN:
    logger.error("❌ DISCORD_TOKEN environment variable not set.")
else:
    logger.info("Starting BOT")
    CLIENT.run(DISCORD_TOKEN)
