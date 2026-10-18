from flask import Flask, request
import os

app = Flask(__name__)

os.makedirs("received_frames", exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload():

    image = request.files["image"]

    filename = image.filename

    save_path = os.path.join("received_frames", filename)

    image.save(save_path)

    print("Image received and saved:", filename)

    return "Image received successfully!", 200


app.run(host="0.0.0.0", port=5000)