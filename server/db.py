import sqlite3
from datetime import datetime, timezone

DB_PATH = "events.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            label TEXT NOT NULL,
            is_healthy INTEGER NOT NULL,
            confidence REAL NOT NULL,
            position TEXT NOT NULL DEFAULT 'unknown'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS irrigation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            moisture REAL NOT NULL,
            pump_status TEXT NOT NULL
        )
    """)
    # Separate history table for the multi-crop specialist model (native app +
    # /predict-v2), kept apart from `detections` so the original web
    # dashboard's history/mission-plan data is never mixed with it.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            label TEXT NOT NULL,
            is_healthy INTEGER NOT NULL,
            confidence REAL NOT NULL,
            position TEXT NOT NULL DEFAULT 'unknown'
        )
    """)
    conn.commit()
    conn.close()


def log_detection(label, is_healthy, confidence, position="unknown"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO detections (timestamp, label, is_healthy, confidence, position) VALUES (?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), label, int(is_healthy), confidence, position),
    )
    conn.commit()
    conn.close()


def log_irrigation(moisture, pump_status):
    conn = get_connection()
    conn.execute(
        "INSERT INTO irrigation_events (timestamp, moisture, pump_status) VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), moisture, pump_status),
    )
    conn.commit()
    conn.close()


def get_all_detections():
    conn = get_connection()
    rows = conn.execute("SELECT timestamp, label, is_healthy, confidence, position FROM detections ORDER BY id").fetchall()
    conn.close()
    return rows


def get_all_irrigation_events():
    conn = get_connection()
    rows = conn.execute("SELECT timestamp, moisture, pump_status FROM irrigation_events ORDER BY id").fetchall()
    conn.close()
    return rows


def get_position_summary():
    """Group all detections by position to surface repeat-offender trees over time."""
    positions = {}
    for timestamp, label, is_healthy, confidence, position in get_all_detections():
        if position not in positions:
            positions[position] = {
                "position": position,
                "total_visits": 0,
                "diseased_count": 0,
                "healthy_count": 0,
                "history": [],
            }
        entry = positions[position]
        entry["total_visits"] += 1
        entry["diseased_count" if not is_healthy else "healthy_count"] += 1
        entry["history"].append({
            "timestamp": timestamp, "label": label, "is_healthy": bool(is_healthy), "confidence": confidence,
        })

    summary = []
    for entry in positions.values():
        latest = entry["history"][-1]
        entry["latest_label"] = latest["label"]
        entry["latest_is_healthy"] = latest["is_healthy"]
        entry["latest_confidence"] = latest["confidence"]
        entry["latest_timestamp"] = latest["timestamp"]
        diseased_confidences = [h["confidence"] for h in entry["history"] if not h["is_healthy"]]
        entry["trend"] = (
            "worsening" if len(diseased_confidences) >= 2 and diseased_confidences[-1] > diseased_confidences[0]
            else "improving" if len(diseased_confidences) >= 2 and diseased_confidences[-1] < diseased_confidences[0]
            else "steady" if len(diseased_confidences) >= 2
            else "new"
        )
        summary.append(entry)

    summary.sort(key=lambda e: (-e["diseased_count"], e["position"]))
    return summary


def log_detection_v2(label, is_healthy, confidence, position="unknown"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO detections_v2 (timestamp, label, is_healthy, confidence, position) VALUES (?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), label, int(is_healthy), confidence, position),
    )
    conn.commit()
    conn.close()


def get_all_detections_v2():
    conn = get_connection()
    rows = conn.execute("SELECT timestamp, label, is_healthy, confidence, position FROM detections_v2 ORDER BY id").fetchall()
    conn.close()
    return rows


def get_position_summary_v2():
    """Same grouping as get_position_summary(), over the v2 (multi-crop) history."""
    positions = {}
    for timestamp, label, is_healthy, confidence, position in get_all_detections_v2():
        if position not in positions:
            positions[position] = {
                "position": position,
                "total_visits": 0,
                "diseased_count": 0,
                "healthy_count": 0,
                "history": [],
            }
        entry = positions[position]
        entry["total_visits"] += 1
        entry["diseased_count" if not is_healthy else "healthy_count"] += 1
        entry["history"].append({
            "timestamp": timestamp, "label": label, "is_healthy": bool(is_healthy), "confidence": confidence,
        })

    summary = []
    for entry in positions.values():
        latest = entry["history"][-1]
        entry["latest_label"] = latest["label"]
        entry["latest_is_healthy"] = latest["is_healthy"]
        entry["latest_confidence"] = latest["confidence"]
        entry["latest_timestamp"] = latest["timestamp"]
        diseased_confidences = [h["confidence"] for h in entry["history"] if not h["is_healthy"]]
        entry["trend"] = (
            "worsening" if len(diseased_confidences) >= 2 and diseased_confidences[-1] > diseased_confidences[0]
            else "improving" if len(diseased_confidences) >= 2 and diseased_confidences[-1] < diseased_confidences[0]
            else "steady" if len(diseased_confidences) >= 2
            else "new"
        )
        summary.append(entry)

    summary.sort(key=lambda e: (-e["diseased_count"], e["position"]))
    return summary
