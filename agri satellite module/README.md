# 🛰️ Agricultural Satellite & Geospatial Integration Module

> **Role:** Person 2 — Satellite / Geospatial Integration  
> **Project:** AI-Based Agricultural Disease Early-Warning System  
> **Target:** Sentinel-2 L2A + Sentinel-1 SAR via Sentinel Hub API + Python FastAPI  
> *(No Google Earth Engine used — strictly Sentinel Hub APIs + Open-Source Geospatial Python)*

Please see the complete documentation and code in [`satellite_module/`](./satellite_module/README.md).

## Quick Start (Windows)

```powershell
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Verify Sentinel Hub Authentication Safely
python satellite_module/verify_sentinelhub_auth.py

# 3. Run unit test suite (32 tests passing)
.venv\Scripts\pytest

# 4. Start the API server
python run.py
```

- **Leaflet Interactive Map UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Standardized Output Endpoint:** `POST http://127.0.0.1:8000/api/satellite/standardized`
- **Output Artifacts:** `satellite_module/outputs/satellite_observation.json` & `satellite_module/outputs/{zone_id}.json`
- **Person 1 Integration Contract:** [`satellite_module/docs/API_CONTRACT.md`](./satellite_module/docs/API_CONTRACT.md)
