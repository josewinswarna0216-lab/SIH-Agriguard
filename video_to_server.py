import cv2
import requests

# Friend's AI server
server_url = "https://handwoven-seduce-degree.ngrok-free.dev/predict"

# Ask for video
video_path = input("Enter video filename: ")

video = cv2.VideoCapture(video_path)

if not video.isOpened():
    print("Could not open video.")
    exit()

fps = video.get(cv2.CAP_PROP_FPS)

print("Video opened successfully!")
print("FPS:", fps)

frame_number = 0
sent_frames = 0

while True:

    success, frame = video.read()

    if not success:
        break

    frame_number += 1

    # Take approximately 1 frame every second
    if frame_number % int(fps) == 0:

        # Resize to 320 x 240
        frame = cv2.resize(frame, (320, 240))

        # Convert frame to JPEG
        success, encoded_frame = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 75]
        )

        if not success:
            print("Could not encode frame.")
            continue

        files = {
            "image": (
                f"frame_{sent_frames + 1}.jpg",
                encoded_frame.tobytes(),
                "image/jpeg"
            )
        }

        data = {
            "position": f"Frame {sent_frames + 1}"
        }

        headers = {
            "ngrok-skip-browser-warning": "true"
        }

        try:

            response = requests.post(
                server_url,
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )

            sent_frames += 1

            print(
                f"\nFrame {sent_frames} sent"
                f"\nServer response: {response.status_code}"
                f"\nAI result: {response.text}"
            )

        except requests.exceptions.RequestException as e:

            print("Error sending frame:", e)

video.release()

print("\nFinished!")
print("Total frames sent:", sent_frames)