from datetime import datetime, timezone
import db
from flight_policy import get_recommended_action

# How long after the last detection we still consider the drone "connected" --
# past this, we assume the flight ended and treat the mission as completed.
CONNECTED_WINDOW_SECONDS = 120

PHASE_LABELS_EN = {
    "idle": "Idle — no mission started",
    "survey": "Survey in progress",
    "orbiting": "Orbiting for closer inspection",
    "completed": "Mission completed",
}
PHASE_LABELS_TA = {
    "idle": "செயலற்றது — பணி தொடங்கவில்லை",
    "survey": "கணக்கெடுப்பு நடைபெறுகிறது",
    "orbiting": "நெருக்கமான ஆய்வுக்காக சுற்றுகிறது",
    "completed": "பணி முடிந்தது",
}


def _seconds_since(iso_timestamp):
    ts = datetime.fromisoformat(iso_timestamp)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


def get_mission_status():
    detections = db.get_all_detections()
    positions = db.get_position_summary()
    trees_scanned = len(positions)

    if not detections:
        return {
            "drone_connected": False,
            "phase": "idle",
            "phase_label": PHASE_LABELS_EN["idle"],
            "phase_label_ta": PHASE_LABELS_TA["idle"],
            "battery_percent": 100,
            "trees_scanned": 0,
        }

    last_timestamp = detections[-1][0]
    elapsed = _seconds_since(last_timestamp)
    drone_connected = elapsed < CONNECTED_WINDOW_SECONDS

    orbiting_now = any(
        get_recommended_action(p["latest_is_healthy"], p["latest_confidence"]) == "extra_orbit"
        for p in positions
    )

    if not drone_connected:
        phase = "completed"
    elif orbiting_now:
        phase = "orbiting"
    else:
        phase = "survey"

    # Simulated telemetry: no real flight controller is attached yet, so this
    # is a simple drain model (battery falls as more trees get scanned) --
    # not a claim of real battery data.
    battery_percent = max(12, 100 - trees_scanned * 4)

    return {
        "drone_connected": drone_connected,
        "phase": phase,
        "phase_label": PHASE_LABELS_EN[phase],
        "phase_label_ta": PHASE_LABELS_TA[phase],
        "battery_percent": battery_percent,
        "trees_scanned": trees_scanned,
    }
