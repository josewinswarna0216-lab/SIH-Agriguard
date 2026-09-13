# ESP32 → Server API Contract

This is what the ESP32 firmware needs to call. The server (Flask + AI model) is already built and running — you just need to POST to these two endpoints.

## Base URL

```
https://handwoven-seduce-degree.ngrok-free.dev
```

**Important:** this URL can change if the tunnel restarts (laptop sleeps, process gets killed, etc). If your requests suddenly start failing, ping back for a fresh URL before debugging anything else.

If you get an HTML page back instead of JSON on your first request, add this header to your HTTP calls:
```
ngrok-skip-browser-warning: true
```

---

## 1. Disease detection — `POST /predict`

Send a captured frame here. Content-Type must be `multipart/form-data`.

**Fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| `image` | file | yes | JPEG frame from the camera. Keep it small — resize to roughly 320×240 at moderate JPEG quality, matching real ESP32-CAM output. Large images (full-res phone photos etc.) can time out over the tunnel. |
| `position` | text | no | Waypoint label, e.g. `"Row 2 - Tree 5"` — matches wherever the simulated flight path is at capture time. Defaults to `"unknown"` if omitted. |

**Example (curl, for testing):**
```bash
curl -X POST \
  -F "image=@frame.jpg" \
  -F "position=Row 2 - Tree 5" \
  https://handwoven-seduce-degree.ngrok-free.dev/predict
```

**Response:**
```json
{
  "status": "Tomato___Late_blight",
  "is_healthy": false,
  "confidence": 0.91,
  "position": "Row 2 - Tree 5",
  "treatment": "Apply fungicide immediately (chlorothalonil); destroy infected plants to prevent spread.",
  "recommended_action": "extra_orbit",
  "recommended_action_label": "Extra low-altitude orbit"
}
```
`recommended_action` is one of `"quick_pass"` (healthy), `"requeue"` (diseased, low confidence — re-check next pass), or `"extra_orbit"` (diseased, confidence > 60% — worth a closer look now).

---

## 2. Irrigation decision — `POST /irrigation-data`

Send a soil moisture reading here. Content-Type must be `application/json`.

**Body:**
```json
{ "moisture": 22 }
```
`moisture` is a percentage (0–100). Below 30% triggers the pump.

**Example (curl):**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"moisture": 22}' \
  https://handwoven-seduce-degree.ngrok-free.dev/irrigation-data
```

**Response:**
```json
{ "pump": "ON" }
```
(`"ON"` or `"OFF"`)

---

## 3. Health check — `GET /health`

Quick connectivity test, no payload needed.

```bash
curl https://handwoven-seduce-degree.ngrok-free.dev/health
```

Response: `{"status": "ok"}`

---

## Notes for the ESP32 firmware

- Arduino's `HTTPClient` doesn't have a built-in multipart helper — you'll need to manually build the multipart body (boundary + headers + JPEG bytes) for the `/predict` call. Happy to hand over a working Arduino snippet for this if useful.
- Every successful call gets logged automatically — results show up live at `https://handwoven-seduce-degree.ngrok-free.dev/dashboard`, so you can watch your requests land in real time while testing.
