from flask import Flask, request, jsonify, render_template, send_file, redirect
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image
import io
import db
import report
from treatments import get_treatment, get_treatment_v2
from translations_ta import get_label_ta, get_treatment_ta
from translations_ta_v2 import get_label_ta_v2, get_treatment_ta_v2
from voice_report import generate_voice_report
from voice_report_v2 import generate_voice_report_v2
from flight_policy import get_recommended_action, get_action_label, get_action_label_ta
from mission_status import get_mission_status

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
db.init_db()

# ---- CONFIG: irrigation threshold ----
MOISTURE_THRESHOLD = 30  # below this percent, pump turns ON
# ---------------------------------------

# ---- CONFIG: update these three to match your Colab training setup ----
MODEL_PATH = "models/plant_disease_model.tflite"
IMG_SIZE = (160, 160)  # must match the input size used during training
CLASS_NAMES = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight", "Corn_(maize)___healthy", "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy", "Potato___Early_blight",
    "Potato___Late_blight", "Potato___healthy", "Raspberry___healthy", "Soybean___healthy",
    "Squash___Powdery_mildew", "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot", "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus", "Tomato___healthy",
]
# -------------------------------------------------------------------------

interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

LAST_FRAME_PATH = "static/last_frame.jpg"
latest_result = None

# ---- Multi-crop specialist model (Friday advancement) ----
# Separate model, class list, interpreter, frame file and in-memory result --
# does not touch or share state with the original 38-class model above.
MODEL_PATH_V2 = "models/plant_disease_model_multicrop.tflite"
IMG_SIZE_V2 = (160, 160)
CLASS_NAMES_V2 = [
    "Banana_Cordana", "Banana_Healthy", "Banana_Pestalotiopsis", "Banana_Sigatoka",
    "Betel_Anthracnose", "Betel_Healthy_Green", "Betel_Healthy_Red", "Betel_Rust",
    "Citrus_Black_spot", "Citrus_Canker", "Citrus_Greening", "Citrus_Healthy",
    "Corn_Blight", "Corn_Common_Rust", "Corn_Gray_Leaf_Spot", "Corn_Healthy",
    "Cotton_Alternaria_Leaf_Spot", "Cotton_Bacterial_Blight", "Cotton_Fusarium_Wilt",
    "Cotton_Healthy", "Cotton_Verticillium_Wilt",
    "Mango_Anthracnose", "Mango_Bacterial_Canker", "Mango_Cutting_Weevil", "Mango_Die_Back",
    "Mango_Gall_Midge", "Mango_Healthy", "Mango_Powdery_Mildew", "Mango_Sooty_Mould",
    "Sugarcane_Healthy", "Sugarcane_Mosaic", "Sugarcane_RedRot", "Sugarcane_Rust", "Sugarcane_Yellow",
]

# ---- Crop-specialist routing (farmer picks their crop in the app) ----
# The model is one shared 34-class CNN, but once the farmer tells us the crop,
# we never need to consider the other 30 classes -- so we mask the output down
# to just that crop's classes and renormalize before picking the answer. This
# is a genuine accuracy win (it can never cross-confuse into the wrong crop's
# disease list) even though it's one network wearing several hats rather than
# separately-trained CNNs -- an honest "Phase 1" a real per-crop model can
# drop into later without changing this routing logic at all.
CROP_CLASS_INDICES = {}
for _idx, _name in enumerate(CLASS_NAMES_V2):
    _crop = _name.split("_", 1)[0]
    CROP_CLASS_INDICES.setdefault(_crop, []).append(_idx)
SUPPORTED_CROPS = list(CROP_CLASS_INDICES.keys())

interpreter_v2 = Interpreter(model_path=MODEL_PATH_V2)
interpreter_v2.allocate_tensors()
input_details_v2 = interpreter_v2.get_input_details()
output_details_v2 = interpreter_v2.get_output_details()

LAST_FRAME_PATH_V2 = "static/last_frame_v2.jpg"
latest_result_v2 = None
# ------------------------------------------------------------


def preprocess(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Resize to fit within IMG_SIZE while preserving aspect ratio, then pad with
    # black to reach exactly IMG_SIZE. A plain .resize(IMG_SIZE) stretches
    # non-square input to fit, distorting the leaf when the source resolution's
    # aspect ratio isn't already 1:1 (e.g. a 1920x1080 drone frame).
    img.thumbnail(IMG_SIZE, Image.LANCZOS)
    padded = Image.new("RGB", IMG_SIZE, (0, 0, 0))
    paste_x = (IMG_SIZE[0] - img.width) // 2
    paste_y = (IMG_SIZE[1] - img.height) // 2
    padded.paste(img, (paste_x, paste_y))

    # NOTE: no /255.0 here — the model's own Rescaling(1./255) layer does this internally.
    # Dividing here too was double-normalizing the input, which is why every prediction looked the same.
    arr = np.array(padded, dtype=np.float32)
    return np.expand_dims(arr, axis=0)


def softmax(logits):
    exp = np.exp(logits - np.max(logits))
    return exp / exp.sum()


@app.route("/")
def root():
    return redirect("/dashboard")


@app.route("/predict", methods=["POST"])
def predict():
    global latest_result

    if "image" not in request.files:
        return jsonify({"error": "no image uploaded"}), 400

    image_bytes = request.files["image"].read()
    input_data = preprocess(image_bytes)

    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]["index"])[0]
    probabilities = softmax(output_data)

    predicted_idx = int(np.argmax(probabilities))
    confidence = float(probabilities[predicted_idx])
    label = CLASS_NAMES[predicted_idx]
    is_healthy = "healthy" in label.lower()
    position = request.form.get("position", "unknown")

    db.log_detection(label, is_healthy, round(confidence, 4), position)

    recommended_action = get_recommended_action(is_healthy, confidence)

    with open(LAST_FRAME_PATH, "wb") as f:
        f.write(image_bytes)

    latest_result = {
        "position": position,
        "label_display": friendly_label(label),
        "is_healthy": is_healthy,
        "confidence": round(confidence * 100, 1),
        "treatment": get_treatment(label),
        "recommended_action_label": get_action_label(recommended_action),
        "timestamp": friendly_time(datetime.now().isoformat()),
    }

    return jsonify({
        "status": label,
        "is_healthy": is_healthy,
        "confidence": round(confidence, 4),
        "position": position,
        "treatment": get_treatment(label),
        "recommended_action": recommended_action,
        "recommended_action_label": get_action_label(recommended_action),
    })


@app.route("/capture")
def capture_page():
    return render_template("capture.html")


@app.route("/stream-frame", methods=["POST"])
def stream_frame():
    # Cheap, frequent preview updates -- no AI inference, no database write.
    # Keeps the visual feed smooth without taxing the model or cluttering
    # detection history with near-duplicate frames every few hundred ms.
    if "image" not in request.files:
        return jsonify({"error": "no image uploaded"}), 400
    image_bytes = request.files["image"].read()
    with open(LAST_FRAME_PATH, "wb") as f:
        f.write(image_bytes)
    return jsonify({"ok": True})


@app.route("/live")
def live_feed():
    return render_template("live.html", result=latest_result)


@app.route("/live-data")
def live_data():
    return jsonify(latest_result or {})


def preprocess_v2(image_bytes):
    # NOTE: plain stretch resize on purpose, NOT the letterbox approach the
    # original preprocess() uses. This model was trained via
    # tf.keras.utils.image_dataset_from_directory, which stretches every
    # image to the target size with no aspect-ratio preservation -- feeding
    # it a letterboxed (black-padded) image at inference time doesn't match
    # what it learned and was measured near-random confidence on real,
    # correctly-labeled training-distribution images until this was caught.
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize(IMG_SIZE_V2, Image.BILINEAR)
    arr = np.array(img, dtype=np.float32)
    return np.expand_dims(arr, axis=0)


def friendly_label_v2(label):
    crop, _, condition = label.partition("_")
    condition = condition.replace("_", " ").strip()
    return f"{crop} — {condition}" if condition else crop


@app.route("/predict-v2", methods=["POST"])
def predict_v2():
    global latest_result_v2

    if "image" not in request.files:
        return jsonify({"error": "no image uploaded"}), 400

    image_bytes = request.files["image"].read()
    input_data = preprocess_v2(image_bytes)

    interpreter_v2.set_tensor(input_details_v2[0]["index"], input_data)
    interpreter_v2.invoke()
    output_data = interpreter_v2.get_tensor(output_details_v2[0]["index"])[0]
    # NOTE: unlike the original model, this model's own final layer already
    # applies softmax (its raw output sums to ~1.0) -- calling softmax() on
    # it again here flattened a genuine ~100% confidence down to ~7%, which
    # is what made every prediction look near-random until this was caught.
    probabilities = output_data

    crop = request.form.get("crop", "").strip()
    specialist_mode = False
    if crop in CROP_CLASS_INDICES:
        indices = CROP_CLASS_INDICES[crop]
        masked = np.full_like(probabilities, -1.0)
        masked[indices] = probabilities[indices]
        total = probabilities[indices].sum()
        if total > 0:
            probabilities = np.where(masked >= 0, probabilities / total, 0.0)
        predicted_idx = int(indices[int(np.argmax(probabilities[indices]))])
        specialist_mode = True
    else:
        predicted_idx = int(np.argmax(probabilities))

    confidence = float(probabilities[predicted_idx])
    label = CLASS_NAMES_V2[predicted_idx]
    is_healthy = "healthy" in label.lower()
    position = request.form.get("position", "unknown")

    db.log_detection_v2(label, is_healthy, round(confidence, 4), position)

    recommended_action = get_recommended_action(is_healthy, confidence)

    with open(LAST_FRAME_PATH_V2, "wb") as f:
        f.write(image_bytes)

    latest_result_v2 = {
        "position": position,
        "label_display": friendly_label_v2(label),
        "label_display_ta": get_label_ta_v2(label),
        "is_healthy": is_healthy,
        "confidence": round(confidence * 100, 1),
        "treatment": get_treatment_v2(label),
        "treatment_ta": get_treatment_ta_v2(label),
        "recommended_action_label": get_action_label(recommended_action),
        "recommended_action_label_ta": get_action_label_ta(recommended_action),
        "timestamp": friendly_time(datetime.now().isoformat()),
    }

    return jsonify({
        "status": label,
        "label_display": friendly_label_v2(label),
        "label_display_ta": get_label_ta_v2(label),
        "is_healthy": is_healthy,
        "confidence": round(confidence, 4),
        "position": position,
        "treatment": get_treatment_v2(label),
        "treatment_ta": get_treatment_ta_v2(label),
        "recommended_action": recommended_action,
        "recommended_action_label": get_action_label(recommended_action),
        "recommended_action_label_ta": get_action_label_ta(recommended_action),
        "specialist_mode": specialist_mode,
        "crop_used": crop if specialist_mode else None,
    })


@app.route("/api/v2/crops")
def api_crops():
    return jsonify({"crops": SUPPORTED_CROPS})


@app.route("/capture-v2")
def capture_page_v2():
    return render_template("capture_v2.html")


@app.route("/stream-frame-v2", methods=["POST"])
def stream_frame_v2():
    if "image" not in request.files:
        return jsonify({"error": "no image uploaded"}), 400
    image_bytes = request.files["image"].read()
    with open(LAST_FRAME_PATH_V2, "wb") as f:
        f.write(image_bytes)
    return jsonify({"ok": True})


@app.route("/live-v2")
def live_feed_v2():
    return render_template("live_v2.html", result=latest_result_v2)


@app.route("/live-data-v2")
def live_data_v2():
    return jsonify(latest_result_v2 or {})


# ---- JSON API for the native app (multi-crop model data) ----
# Plain HTTP handlers, not blueprints -- the rest of this file already keeps
# things flat, and a handful of read-only routes doesn't earn the extra
# indirection.

def _v2_detection_json(timestamp, label, is_healthy, confidence, position):
    recommended_action = get_recommended_action(bool(is_healthy), confidence)
    return {
        "timestamp": friendly_time(timestamp),
        "label": label,
        "label_display": friendly_label_v2(label),
        "label_display_ta": get_label_ta_v2(label),
        "is_healthy": bool(is_healthy),
        "confidence": round(confidence * 100, 1),
        "position": position,
        "treatment": get_treatment_v2(label) if not is_healthy else None,
        "treatment_ta": get_treatment_ta_v2(label) if not is_healthy else None,
        "recommended_action": recommended_action,
        "recommended_action_label": get_action_label(recommended_action),
        "recommended_action_label_ta": get_action_label_ta(recommended_action),
    }


@app.route("/api/v2/detections")
def api_v2_detections():
    rows = db.get_all_detections_v2()
    detections = [_v2_detection_json(*row) for row in rows]
    return jsonify(list(reversed(detections[-100:])))


@app.route("/api/v2/summary")
def api_v2_summary():
    rows = db.get_all_detections_v2()
    detections = [_v2_detection_json(*row) for row in rows]
    diseased_count = sum(1 for d in detections if not d["is_healthy"])
    healthy_count = len(detections) - diseased_count
    positions = db.get_position_summary_v2()
    field_status = (
        "urgent" if any(p["trend"] == "worsening" for p in positions if not p["latest_is_healthy"])
        else "attention" if diseased_count > 0
        else "good"
    )
    return jsonify({
        "total_detections": len(detections),
        "healthy_count": healthy_count,
        "diseased_count": diseased_count,
        "field_status": field_status,
        "latest": detections[-1] if detections else None,
    })


@app.route("/api/v2/positions")
def api_v2_positions():
    positions = db.get_position_summary_v2()
    result = []
    for p in positions:
        action = get_recommended_action(p["latest_is_healthy"], p["latest_confidence"])
        result.append({
            "position": p["position"],
            "total_visits": p["total_visits"],
            "diseased_count": p["diseased_count"],
            "healthy_count": p["healthy_count"],
            "trend": p["trend"],
            "latest_label_display": friendly_label_v2(p["latest_label"]),
            "latest_label_display_ta": get_label_ta_v2(p["latest_label"]),
            "latest_is_healthy": p["latest_is_healthy"],
            "latest_confidence": round(p["latest_confidence"] * 100, 1),
            "latest_timestamp": friendly_time(p["latest_timestamp"]),
            "latest_treatment": get_treatment_v2(p["latest_label"]) if not p["latest_is_healthy"] else None,
            "latest_treatment_ta": get_treatment_ta_v2(p["latest_label"]) if not p["latest_is_healthy"] else None,
            "recommended_action": action,
            "recommended_action_label": get_action_label(action),
            "recommended_action_label_ta": get_action_label_ta(action),
        })
    return jsonify(result)


@app.route("/api/v2/mission-plan")
def api_v2_mission_plan():
    positions_by_label = {p["position"]: p for p in db.get_position_summary_v2()}

    grid = []
    for r in range(MISSION_ROWS):
        for t in range(MISSION_TREES_PER_ROW):
            label = f"Row {r + 1} - Tree {t + 1}"
            data = positions_by_label.get(label)
            cell = {
                "position": label,
                "cx": MISSION_COL_X[t],
                "cy": MISSION_ROW_Y[r],
                "visited": data is not None,
            }
            if data:
                action = get_recommended_action(data["latest_is_healthy"], data["latest_confidence"])
                cell.update({
                    "is_healthy": data["latest_is_healthy"],
                    "label_display": friendly_label_v2(data["latest_label"]),
                    "label_display_ta": get_label_ta_v2(data["latest_label"]),
                    "confidence": round(data["latest_confidence"] * 100, 1),
                    "treatment": get_treatment_v2(data["latest_label"]) if not data["latest_is_healthy"] else None,
                    "treatment_ta": get_treatment_ta_v2(data["latest_label"]) if not data["latest_is_healthy"] else None,
                    "recommended_action": action,
                    "recommended_action_label": get_action_label(action),
                    "recommended_action_label_ta": get_action_label_ta(action),
                })
            grid.append(cell)

    irrigation_rows = db.get_all_irrigation_events()
    latest_irrigation = None
    if irrigation_rows:
        _, moisture, pump = irrigation_rows[-1]
        latest_irrigation = {"moisture": moisture, "pump_status": pump}

    return jsonify({
        "grid": grid,
        "base": MISSION_BASE,
        "latest_irrigation": latest_irrigation,
    })


@app.route("/voice-report-v2/<lang>")
def voice_report_audio_v2(lang):
    if lang not in ("en", "ta"):
        return jsonify({"error": "lang must be 'en' or 'ta'"}), 400
    path = generate_voice_report_v2(lang)
    return send_file(path, mimetype="audio/mpeg")


@app.route("/api/irrigation")
def api_irrigation():
    rows = db.get_all_irrigation_events()
    events = [
        {"timestamp": friendly_time(t), "moisture": m, "pump_status": p}
        for t, m, p in rows
    ]
    return jsonify({
        "latest": events[-1] if events else None,
        "events": list(reversed(events[-20:])),
    })
# ---------------------------------------------------------------


@app.route("/irrigation-data", methods=["POST"])
def irrigation_data():
    payload = request.get_json(silent=True)
    if not payload or "moisture" not in payload:
        return jsonify({"error": "expected JSON body with a 'moisture' field"}), 400

    moisture = float(payload["moisture"])
    pump_status = "ON" if moisture < MOISTURE_THRESHOLD else "OFF"

    db.log_irrigation(moisture, pump_status)

    return jsonify({"pump": pump_status})


LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def friendly_time(iso_timestamp):
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        # Timestamps are stored in UTC (db.py uses datetime.now(timezone.utc));
        # convert to local time before formatting, or every displayed time
        # shows up 5.5 hours behind what actually happened.
        if dt.tzinfo is not None:
            dt = dt.astimezone(LOCAL_TZ)
        return dt.strftime("%b %d, %I:%M %p").replace(" 0", " ")
    except (ValueError, TypeError):
        return iso_timestamp


def friendly_label(label):
    crop, _, condition = label.partition("___")
    crop = crop.replace("_", " ").replace(",", "")
    condition = condition.replace("_", " ").strip()
    if not condition or condition.lower() == "healthy":
        return f"{crop} — Healthy"
    return f"{crop} — {condition}"


@app.route("/dashboard")
def dashboard():
    detection_rows = db.get_all_detections()
    irrigation_rows = db.get_all_irrigation_events()

    detections = [
        {
            "timestamp": friendly_time(t), "label": l, "label_display": friendly_label(l), "label_display_ta": get_label_ta(l),
            "is_healthy": bool(h), "confidence": c, "position": p,
            "treatment": get_treatment(l), "treatment_ta": get_treatment_ta(l),
        }
        for t, l, h, c, p in detection_rows
    ]
    irrigation_events = [
        {"timestamp": friendly_time(t), "moisture": m, "pump_status": p}
        for t, m, p in irrigation_rows
    ]
    latest = detections[-1] if detections else None

    # Every position whose most recent visit is diseased — not just ones flagged more than once.
    # A single day's grid survey visits each tree only once, so gating on repeats would hide real findings.
    action_items = [p for p in db.get_position_summary() if not p["latest_is_healthy"]]
    action_items.sort(key=lambda o: (-o["diseased_count"], o["latest_timestamp"]))
    for o in action_items:
        o["latest_label_display"] = friendly_label(o["latest_label"])
        o["latest_label_display_ta"] = get_label_ta(o["latest_label"])
        o["latest_treatment"] = get_treatment(o["latest_label"])
        o["latest_treatment_ta"] = get_treatment_ta(o["latest_label"])
        o["recommended_action"] = get_recommended_action(o["latest_is_healthy"], o["latest_confidence"])
        o["recommended_action_label"] = get_action_label(o["recommended_action"])
        o["recommended_action_label_ta"] = get_action_label_ta(o["recommended_action"])
        o["latest_timestamp"] = friendly_time(o["latest_timestamp"])

    diseased_count = sum(1 for d in detections if not d["is_healthy"])
    field_status = (
        "urgent" if any(o["trend"] == "worsening" for o in action_items)
        else "attention" if diseased_count > 0
        else "good"
    )

    return render_template(
        "dashboard.html",
        detections=list(reversed(detections[-10:])),
        irrigation_events=list(reversed(irrigation_events[-10:])),
        latest_detection=latest,
        latest_irrigation=irrigation_events[-1] if irrigation_events else None,
        total_detections=len(detections),
        healthy_count=sum(1 for d in detections if d["is_healthy"]),
        diseased_count=diseased_count,
        total_irrigation=len(irrigation_events),
        repeat_offenders=action_items,
        field_status=field_status,
        mission=get_mission_status(),
    )


@app.route("/overview")
def overview():
    return render_template("overview.html")


MISSION_ROWS = 5
MISSION_TREES_PER_ROW = 3
MISSION_COL_X = [250, 400, 550]
MISSION_ROW_Y = [120, 220, 320, 420, 520]
MISSION_BASE = {"x": 100, "y": 620}


@app.route("/mission-plan")
def mission_plan():
    positions_by_label = {p["position"]: p for p in db.get_position_summary()}

    grid = []
    for r in range(MISSION_ROWS):
        for t in range(MISSION_TREES_PER_ROW):
            label = f"Row {r + 1} - Tree {t + 1}"
            data = positions_by_label.get(label)
            cell = {
                "position": label,
                "cx": MISSION_COL_X[t],
                "cy": MISSION_ROW_Y[r],
                "visited": data is not None,
            }
            if data:
                action = get_recommended_action(data["latest_is_healthy"], data["latest_confidence"])
                cell.update({
                    "is_healthy": data["latest_is_healthy"],
                    "label_display": friendly_label(data["latest_label"]),
                    "confidence": data["latest_confidence"],
                    "treatment": get_treatment(data["latest_label"]) if not data["latest_is_healthy"] else None,
                    "recommended_action": action,
                    "recommended_action_label": get_action_label(action),
                })
            grid.append(cell)

    irrigation_rows = db.get_all_irrigation_events()
    latest_irrigation = None
    if irrigation_rows:
        _, moisture, pump = irrigation_rows[-1]
        latest_irrigation = {"moisture": moisture, "pump_status": pump}

    action_items = [p for p in db.get_position_summary() if not p["latest_is_healthy"]]
    action_items.sort(key=lambda o: (-o["diseased_count"], o["latest_timestamp"]))
    top_flag = action_items[0] if action_items else None

    return render_template(
        "mission_plan.html",
        mission=get_mission_status(),
        top_flag=top_flag,
        grid=grid,
        base=MISSION_BASE,
        latest_irrigation=latest_irrigation,
    )


@app.route("/report")
def get_report():
    path = report.build_report()
    return send_file(path, as_attachment=True)


@app.route("/voice-report/<lang>")
def voice_report_audio(lang):
    if lang not in ("en", "ta"):
        return jsonify({"error": "lang must be 'en' or 'ta'"}), 400
    path = generate_voice_report(lang)
    return send_file(path, mimetype="audio/mpeg")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# Absolute path to the built debug APK, so teammates on the same WiFi can
# grab the native app straight from this server -- no Play Store, no cable.
ANDROID_APK_PATH = "/Users/josewin/sih-agri-drone/android/app/build/outputs/apk/debug/app-debug.apk"


@app.route("/download-app")
def download_app():
    if not os.path.exists(ANDROID_APK_PATH):
        return jsonify({"error": "APK not built yet"}), 404
    return send_file(ANDROID_APK_PATH, as_attachment=True, download_name="AgriGuard.apk")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
