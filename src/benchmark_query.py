"""
Standard query against ollama server for benchmark metrics.
"""

import json
import requests

URL = "http://localhost:11434/api/generate"
HEADERS = {"Content-Type": "application/json"}
DATA = {
    "model": "llama3",
    "prompt": "Write a short story about a robot and a cat",
    "max_tokens": 100,
    "temperature": 0.1,
    "stream": False
}

response = requests.post(URL, headers=HEADERS, data=json.dumps(DATA), timeout=5000)
result = response.json()

if "response" in result:
    print(result["response"])
else:
    print("No response received")
