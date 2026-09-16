"""Root runner shortcut for the Satellite / Geospatial Integration Module."""

import sys
from pathlib import Path

# Add satellite_module to path
MODULE_DIR = Path(__file__).resolve().parent / "satellite_module"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("🛰️  SATELLITE / GEOSPATIAL INTEGRATION MODULE")
    print(f"Mode: {'DEMO MODE (Simulated Satellite Data)' if settings.DEMO_MODE else 'LIVE SENTINEL-2 L2A API'}")
    print(f"Server URL: http://{settings.HOST}:{settings.PORT}")
    print(f"Swagger API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Leaflet Test Interface: http://{settings.HOST}:{settings.PORT}/")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
