import requests

def get_craiyon_images(prompt: str):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.post(
            "https://backend.craiyon.com/generate",
            json={"prompt": prompt},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if "images" not in data:
            return {"error": "No images found."}
        return [f"data:image/jpeg;base64,{img}" for img in data["images"]]
    except requests.RequestException as e:
        return {"error": str(e)}

get_craiyon_images("Create an image of a green bean on a plate, in line-drawing style.")
