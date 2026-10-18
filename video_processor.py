import cv2

video = cv2.VideoCapture("test_video.mp4")

if not video.isOpened():
    print("Could not open video")
    exit()

fps = video.get(cv2.CAP_PROP_FPS)

print("Video FPS:", fps)

frame_number = 0
captured_frames = 0

while True:
    success, frame = video.read()

    if not success:
        break

    frame_number += 1

    # Capture 1 frame every second
    if frame_number % int(fps) == 0:

        captured_frames += 1

        filename = f"frame_{captured_frames}.jpg"

        cv2.imwrite(filename, frame)

        print("Captured:", filename)

video.release()

print("Total frames captured:", captured_frames)