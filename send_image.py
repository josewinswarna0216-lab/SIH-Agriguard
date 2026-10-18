import requests

server_url = "http://127.0.0.1:5000/upload"

with open("frame_1.jpg", "rb") as image:
    files = {
        "image": image
    }

    response = requests.post(server_url, files=files)

print("Server response:", response.text)