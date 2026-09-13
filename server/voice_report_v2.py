import os
from gtts import gTTS
import db
from treatments import get_treatment_v2
from translations_ta_v2 import get_label_ta_v2, get_treatment_ta_v2

TREND_TA = {"worsening": "மோசமடைந்து வருகிறது", "improving": "மேம்பட்டு வருகிறது", "steady": "நிலையாக உள்ளது", "new": "புதிதாக கண்டறியப்பட்டது"}

AUDIO_DIR = "audio"


def _field_data():
    detections = db.get_all_detections_v2()
    irrigation_events = db.get_all_irrigation_events()
    total = len(detections)

    action_items = [p for p in db.get_position_summary_v2() if not p["latest_is_healthy"]]
    action_items.sort(key=lambda o: (-o["diseased_count"], o["latest_timestamp"]))

    latest_irrigation = irrigation_events[-1] if irrigation_events else None
    return total, action_items, latest_irrigation


def build_summary_text_v2(lang):
    total, action_items, latest_irrigation = _field_data()

    if lang == "ta":
        parts = [f"பல பயிர் ஆரோக்கிய புதுப்பிப்பு. இன்று {total} செடிகள் ஆய்வு செய்யப்பட்டன."]
        if action_items:
            parts.append(f"{len(action_items)} இடங்களில் நோய் கண்டறியப்பட்டது.")
            top = action_items[0]
            label_ta = get_label_ta_v2(top["latest_label"])
            trend_ta = TREND_TA.get(top["trend"], top["trend"])
            parts.append(
                f"மிக அதிகமாக பாதிக்கப்பட்டது {top['position']}. நோய்: {label_ta}. "
                f"{top['total_visits']} இல் {top['diseased_count']} முறை கண்டறியப்பட்டது. நிலை {trend_ta}."
            )
            parts.append(f"பரிந்துரை: {get_treatment_ta_v2(top['latest_label'])}")
        else:
            parts.append("அனைத்து செடிகளும் ஆரோக்கியமாக உள்ளன. எந்த நடவடிக்கையும் தேவையில்லை.")
        if latest_irrigation:
            _, moisture, pump = latest_irrigation
            pump_ta = "இயங்குகிறது" if pump == "ON" else "நிறுத்தப்பட்டுள்ளது"
            parts.append(f"மண் ஈரப்பதம் {moisture} சதவீதம். பம்ப் தற்போது {pump_ta}.")
        return " ".join(parts)

    parts = [f"Multi-crop field health update. {total} plants inspected today."]
    if action_items:
        parts.append(f"{len(action_items)} position{'s' if len(action_items) != 1 else ''} currently show disease.")
        top = action_items[0]
        label_en = top["latest_label"].replace("_", " ")
        parts.append(
            f"The most affected is {top['position']}. Condition: {label_en}. "
            f"Flagged {top['diseased_count']} of {top['total_visits']} visits. Trend is {top['trend']}."
        )
        parts.append(f"Recommended treatment: {get_treatment_v2(top['latest_label'])}")
    else:
        parts.append("All plants are healthy. No action needed.")
    if latest_irrigation:
        _, moisture, pump = latest_irrigation
        parts.append(f"Soil moisture is {moisture} percent. Pump is currently {'running' if pump == 'ON' else 'off'}.")
    return " ".join(parts)


def generate_voice_report_v2(lang):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    text = build_summary_text_v2(lang)
    path = f"{AUDIO_DIR}/report_v2_{lang}.mp3"
    gTTS(text=text, lang=lang).save(path)
    return path
