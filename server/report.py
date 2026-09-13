from datetime import datetime
from fpdf import FPDF
import db
from treatments import get_treatment
from translations_ta import get_label_ta, get_treatment_ta

TREND_TA = {"worsening": "மோசமடைகிறது", "improving": "மேம்படுகிறது", "steady": "நிலையானது", "new": "புதியது"}


def build_report():
    detections = db.get_all_detections()
    irrigation_events = db.get_all_irrigation_events()

    healthy_count = sum(1 for d in detections if d[2])
    diseased_count = len(detections) - healthy_count
    pump_on_count = sum(1 for e in irrigation_events if e[2] == "ON")

    disease_counts = {}
    diseased_positions = []
    for _, label, is_healthy, _, position in detections:
        if not is_healthy:
            disease_counts[label] = disease_counts.get(label, 0) + 1
            diseased_positions.append((position, label))

    # Every position whose most recent visit is diseased — matches the dashboard's "Action Needed" logic.
    # A single day's grid survey visits each tree only once, so gating on repeats would hide real findings.
    action_items = [p for p in db.get_position_summary() if not p["latest_is_healthy"]]
    action_items.sort(key=lambda o: (-o["diseased_count"], o["latest_timestamp"]))

    pdf = FPDF()
    pdf.add_font("NotoTamil", "", "fonts/NotoSansTamil.ttf")

    # ---------------- ENGLISH PAGE ----------------
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Autonomous Inspection Scout Drone", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Daily Inspection Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Total plants inspected: {len(detections)}", ln=True)
    pdf.cell(0, 7, f"Healthy: {healthy_count}    Diseased: {diseased_count}", ln=True)
    pdf.cell(0, 7, f"Irrigation events: {len(irrigation_events)} (pump activated {pump_on_count} times)", ln=True)
    pdf.ln(6)

    if disease_counts:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Disease Breakdown", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for label, count in sorted(disease_counts.items(), key=lambda x: -x[1]):
            pdf.cell(0, 7, f"  {label}: {count}", ln=True)
        pdf.ln(6)

    if diseased_positions:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Diseased Plant Locations", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for position, label in diseased_positions:
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 7, f"  {position}  -  {label}", ln=True)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 6, f"      Recommended: {get_treatment(label)}")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 11)
        pdf.ln(4)

    if action_items:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Positions Needing Attention", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for o in action_items:
            pdf.cell(0, 7, f"  {o['position']}: {o['diseased_count']} of {o['total_visits']} visits diseased - trend: {o['trend']}", ln=True)
        pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Detection Log", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for timestamp, label, is_healthy, confidence, position in detections:
        status = "Healthy" if is_healthy else "Diseased"
        pdf.cell(0, 6, f"{timestamp}  |  {position}  |  {label}  |  {status}  |  {confidence * 100:.1f}%", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Irrigation Log", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for timestamp, moisture, pump_status in irrigation_events:
        pdf.cell(0, 6, f"{timestamp}  |  Moisture: {moisture}%  |  Pump: {pump_status}", ln=True)

    # ---------------- TAMIL PAGE ----------------
    pdf.add_page()
    pdf.set_font("NotoTamil", "", 18)
    pdf.cell(0, 10, "தன்னியக்க ஆய்வு ஸ்கவுட் ட்ரோன்", ln=True)
    pdf.set_font("NotoTamil", "", 12)
    pdf.cell(0, 8, "தினசரி ஆய்வு அறிக்கை", ln=True)
    pdf.set_font("NotoTamil", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"உருவாக்கப்பட்டது: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.set_font("NotoTamil", "", 13)
    pdf.cell(0, 8, "சுருக்கம்", ln=True)
    pdf.set_font("NotoTamil", "", 11)
    pdf.cell(0, 7, f"மொத்த ஆய்வு செய்யப்பட்ட செடிகள்: {len(detections)}", ln=True)
    pdf.cell(0, 7, f"ஆரோக்கியமானவை: {healthy_count}    நோய்வாய்ப்பட்டவை: {diseased_count}", ln=True)
    pdf.cell(0, 7, f"நீர்ப்பாசன நிகழ்வுகள்: {len(irrigation_events)} (பம்ப் {pump_on_count} முறை இயக்கப்பட்டது)", ln=True)
    pdf.ln(6)

    if disease_counts:
        pdf.set_font("NotoTamil", "", 13)
        pdf.cell(0, 8, "நோய் பிரிவு", ln=True)
        pdf.set_font("NotoTamil", "", 11)
        for label, count in sorted(disease_counts.items(), key=lambda x: -x[1]):
            pdf.cell(0, 7, f"  {get_label_ta(label)}: {count}", ln=True)
        pdf.ln(6)

    if diseased_positions:
        pdf.set_font("NotoTamil", "", 13)
        pdf.cell(0, 8, "நோய்வாய்ப்பட்ட செடிகளின் இடங்கள்", ln=True)
        pdf.set_font("NotoTamil", "", 11)
        for position, label in diseased_positions:
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 7, f"  {position}  -  {get_label_ta(label)}", ln=True)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("NotoTamil", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 6, f"      பரிந்துரை: {get_treatment_ta(label)}")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("NotoTamil", "", 11)
        pdf.ln(4)

    if action_items:
        pdf.set_font("NotoTamil", "", 13)
        pdf.cell(0, 8, "கவனம் தேவைப்படும் இடங்கள்", ln=True)
        pdf.set_font("NotoTamil", "", 11)
        for o in action_items:
            trend_ta = TREND_TA.get(o["trend"], o["trend"])
            pdf.cell(0, 7, f"  {o['position']}: {o['total_visits']} இல் {o['diseased_count']} முறை - போக்கு: {trend_ta}", ln=True)
        pdf.ln(6)

    pdf.set_font("NotoTamil", "", 13)
    pdf.cell(0, 8, "ஆய்வு பதிவு", ln=True)
    pdf.set_font("NotoTamil", "", 9)
    for timestamp, label, is_healthy, confidence, position in detections:
        status = "ஆரோக்கியம்" if is_healthy else "நோய்வாய்ப்பட்டது"
        pdf.cell(0, 6, f"{timestamp}  |  {position}  |  {get_label_ta(label)}  |  {status}  |  {confidence * 100:.1f}%", ln=True)
    pdf.ln(6)

    pdf.set_font("NotoTamil", "", 13)
    pdf.cell(0, 8, "நீர்ப்பாசன பதிவு", ln=True)
    pdf.set_font("NotoTamil", "", 9)
    for timestamp, moisture, pump_status in irrigation_events:
        pump_ta = "ஆன்" if pump_status == "ON" else "ஆஃப்"
        pdf.cell(0, 6, f"{timestamp}  |  ஈரப்பதம்: {moisture}%  |  பம்ப்: {pump_ta}", ln=True)

    output_path = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(output_path)
    return output_path
