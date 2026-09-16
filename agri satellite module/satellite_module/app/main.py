"""FastAPI application entry point for Satellite / Geospatial Integration Module."""

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings, OUTPUTS_DIR, BASE_DIR
from .api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("satellite_module")

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"Starting Satellite Module (DEMO_MODE={settings.DEMO_MODE}, "
        f"HEALTHY_THRESH={settings.NDVI_HEALTHY_THRESHOLD}, "
        f"MODERATE_THRESH={settings.NDVI_MODERATE_THRESHOLD})"
    )
    if settings.DEMO_MODE:
        logger.info("Operating in DEMO_MODE: Ready to demonstrate without live Sentinel Hub credentials.")
    else:
        logger.info("Operating in LIVE mode with Sentinel Hub Process API.")
    yield


app = FastAPI(
    title="Agricultural Satellite / Geospatial Integration Module",
    description=(
        "Sentinel-2 L2A satellite data pipeline for vegetation stress detection, "
        "cloud filtering, NDVI computation, and GeoJSON affected-zone vectorization."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for external integration (Person 1's backend / frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs directory to serve generated maps and GeoJSON
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Static directory for Leaflet test interface
STATIC_DIR = BASE_DIR / "app" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", include_in_schema=False)
def serve_ui():
    """Serve the Leaflet/OpenStreetMap web testing interface."""
    index_html = STATIC_DIR / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return {
        "message": "Satellite Module API is running. Access interactive docs at /docs or /health.",
        "version": "1.0.0",
        "demo_mode": settings.DEMO_MODE
    }


# Include API endpoints
app.include_router(router)
