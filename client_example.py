"""
Example client for the AgriGuard AI server.

This shows the minimum code needed to send a leaf photo to the trained
AI model and get back a disease diagnosis. Swap SERVER_URL and IMAGE_PATH
for your own values and run it.

Install requirements first:
    pip install requests
"""

import requests

SERVER_URL = "https://handwoven-seduce-degree.ngrok-free.dev/predict"
IMAGE_PATH = "leaf.jpg"      # path to a leaf photo on your machine
POSITION = "Row 1 - Tree 1"  # optional label for where this photo was taken


def detect_disease(image_path, position="unknown"):
    with open(image_path, "rb") as f:
        files = {"image": (image_path, f, "image/jpeg")}
        data = {"position": position}
        headers = {"ngrok-skip-browser-warning": "true"}  # required for ngrok's free tier

        response = requests.post(SERVER_URL, files=files, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    result = detect_disease(IMAGE_PATH, POSITION)

    print("Diagnosis:", result["status"])
    print("Healthy:", result["is_healthy"])
    print("Confidence:", f"{result['confidence'] * 100:.1f}%")
    print("Treatment:", result["treatment"])
    print("Recommended next pass:", result["recommended_action_label"])
