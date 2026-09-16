"""FastAPI route handlers for satellite imagery analysis and vegetation stress detection."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from fastapi import APIRouter, HTTPException, status
from shapely.geometry import Polygon, Point
import shapely

from ..config import settings, OUTPUTS_DIR
from ..models.schemas import (
    SatelliteAnalysisRequest,
    SatelliteAnalysisResponse,
    NDVIRequest,
    SatelliteInfo,
    VegetationStats,
    StressStats,
    OutputFiles,
    GeoJSONFeatureCollection,
    HealthResponse
)
from ..geospatial.polygon import parse_polygon_input
from ..geospatial.area import calculate_polygon_area_hectares, calculate_mask_area_hectares
from ..geospatial.geojson import vectorize_mask_to_geojson
from ..satellite.imagery import Sentinel2Service, Sentinel1Service, NoSatelliteImageFoundError, CloudCoverExceededError
from ..satellite.cloud_mask import apply_scl_cloud_mask
from ..satellite.sentinelhub_client import check_sentinelhub_connection
from ..satellite.standardized import build_standardized_output, save_standardized_json
from ..models.standardized_schema import StandardizedSatelliteOutput
from ..analysis.ndvi import compute_vegetation_statistics
from ..analysis.stress import classify_vegetation_stress, generate_ndvi_and_stress_maps
from ..analysis.baseline import compare_with_historical_baseline

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for recently analyzed fields
RECENT_RESULTS: Dict[str, Dict[str, Any]] = {}


def _rasterize_farm_mask(polygon: Polygon, height: int, width: int) -> np.ndarray:
    """Rasterize a Shapely polygon to a boolean 2D mask matching the satellite raster dimensions."""
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    xs = np.linspace(min_lon, max_lon, width)
    ys = np.linspace(max_lat, min_lat, height)
    xv, yv = np.meshgrid(xs, ys)

    # Use Shapely 2.0 vectorized contains_xy if available, else prepared geometry
    if hasattr(shapely, "contains_xy"):
        mask = shapely.contains_xy(polygon, xv, yv)
    else:
        from shapely.prepared import prep
        prepared_poly = prep(polygon)
        mask = np.zeros((height, width), dtype=bool)
        for r in range(height):
            for c in range(width):
                mask[r, c] = prepared_poly.contains(Point(xv[r, c], yv[r, c]))

    # If polygon is very small or irregular and points missed, mark all as true inside bbox
    if not np.any(mask):
        mask.fill(True)

    return mask


@router.get("/health", response_model=HealthResponse, summary="Service health status")
def health_check():
    """Returns the operational health of the satellite module and Sentinel Hub configuration."""
    conn_info = check_sentinelhub_connection()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        demo_mode=settings.DEMO_MODE,
        sentinelhub_configured=conn_info["authenticated"]
    )


@router.post(
    "/api/satellite/analyze",
    response_model=SatelliteAnalysisResponse,
    summary="Complete satellite stress analysis pipeline",
    status_code=status.HTTP_200_OK
)
def analyze_satellite_data(request: SatelliteAnalysisRequest):
    """Executes the complete satellite and geospatial analysis pipeline:

    1. Parses and validates the farm boundary polygon.
    2. Searches and retrieves Sentinel-2 L2A multispectral imagery.
    3. Filters clouds, shadows, and invalid pixels using Scene Classification (SCL).
    4. Calculates NDVI vegetation index.
    5. Detects potential vegetation stress / anomalies (Healthy, Moderate, High).
    6. Vectorizes high-stress pixel clusters into clean GeoJSON polygons clipped to farm boundary.
    7. Computes accurate ellipsoidal geodesic surface areas in hectares.
    8. Generates visual NDVI and stress PNG maps.
    9. Returns complete JSON integration payload.
    """
    logger.info(f"Received analysis request for field_id: {request.field_id}, crop: {request.crop}")

    # 1. Parse & validate farm polygon
    try:
        farm_poly = parse_polygon_input(polygon_input=request.polygon, bbox_input=request.bbox)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid farm boundary input: {str(val_err)}"
        )

    # Validate farm area (minimum threshold check)
    total_farm_ha = calculate_polygon_area_hectares(farm_poly)
    if total_farm_ha < 0.001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Farm polygon is too small ({total_farm_ha:.4f} ha). Minimum area of 0.01 hectares required."
        )

    # Validate dates
    start_dt_str = str(request.start_date)
    end_dt_str = str(request.end_date)
    if start_dt_str > end_dt_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date range: start_date ({start_dt_str}) is after end_date ({end_dt_str})."
        )

    # 2. Acquire Sentinel-2 satellite data
    try:
        service = Sentinel2Service()
        data = service.search_and_download(
            polygon=farm_poly,
            start_date=start_dt_str,
            end_date=end_dt_str,
            max_cloud_cover=request.max_cloud_cover
        )
    except NoSatelliteImageFoundError as no_img_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(no_img_err)
        )
    except CloudCoverExceededError as cloud_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(cloud_err)
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED if "authentication" in str(val_err).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        logger.error(f"Unexpected error acquiring satellite imagery: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing satellite imagery: {str(exc)}"
        )

    ndvi = data["ndvi"]
    scl = data["scl"]
    datamask = data["datamask"]
    image_date = data["image_date"]
    cloud_percentage = data["cloud_percentage"]
    is_simulated = data["is_simulated"]

    # 3. Create raster farm mask and apply cloud filtering (SCL)
    height, width = ndvi.shape
    farm_mask = _rasterize_farm_mask(farm_poly, height, width)
    valid_mask = apply_scl_cloud_mask(scl, datamask, farm_mask=farm_mask)

    # 4. Compute NDVI statistics over valid vegetation pixels
    veg_stats = compute_vegetation_statistics(ndvi, valid_mask)

    # 5. Stress classification (HEALTHY, MODERATE, HIGH)
    stress_grid, overall_level, high_stress_mask = classify_vegetation_stress(
        ndvi=ndvi,
        valid_mask=valid_mask,
        healthy_threshold=settings.NDVI_HEALTHY_THRESHOLD,
        moderate_threshold=settings.NDVI_MODERATE_THRESHOLD
    )

    # 6. Vectorize high-stress mask into GeoJSON polygons & clip to farm boundary
    fc_dict, clipped_polys = vectorize_mask_to_geojson(
        field_id=request.field_id,
        high_stress_mask=high_stress_mask,
        ndvi=ndvi,
        farm_polygon=farm_poly,
        min_area_hectares=settings.MIN_STRESS_AREA_HECTARES
    )

    # 7. Accurate geodesic area calculations
    total_area_ha, stressed_ha, stressed_pct = calculate_mask_area_hectares(clipped_polys, farm_poly)

    # 8. Historical baseline comparison (optional)
    baseline_info = {"baseline_mean_ndvi": None, "ndvi_change": None, "ndvi_change_percentage": None}
    if request.baseline_start_date and request.baseline_end_date:
        try:
            b_data = service.search_and_download(
                polygon=farm_poly,
                start_date=str(request.baseline_start_date),
                end_date=str(request.baseline_end_date),
                max_cloud_cover=request.max_cloud_cover
            )
            b_farm_mask = _rasterize_farm_mask(farm_poly, b_data["ndvi"].shape[0], b_data["ndvi"].shape[1])
            b_valid = apply_scl_cloud_mask(b_data["scl"], b_data["datamask"], farm_mask=b_farm_mask)
            b_stats = compute_vegetation_statistics(b_data["ndvi"], b_valid)
            baseline_info = compare_with_historical_baseline(
                current_mean_ndvi=veg_stats["mean_ndvi"],
                baseline_mean_ndvi=b_stats["mean_ndvi"]
            )
        except Exception as b_exc:
            logger.warning(f"Could not retrieve historical baseline: {b_exc}")

    # 9. Generate visual maps (NDVI and stress maps)
    ndvi_map_path, stress_map_path = generate_ndvi_and_stress_maps(
        field_id=request.field_id,
        ndvi=ndvi,
        valid_mask=valid_mask,
        stress_grid=stress_grid
    )

    # Format URLs for generated output artifacts
    outputs = OutputFiles(
        ndvi_map=f"/outputs/{request.field_id}_ndvi.png",
        stress_map=f"/outputs/{request.field_id}_stress.png",
        affected_geojson=f"/outputs/{request.field_id}_affected.geojson"
    )

    # Assemble response payload
    response = SatelliteAnalysisResponse(
        field_id=request.field_id,
        crop=request.crop,
        analysis_timestamp=datetime.utcnow().isoformat() + "Z",
        is_simulated=is_simulated,
        satellite=SatelliteInfo(
            source="Sentinel-2",
            processing_level="L2A",
            image_date=image_date,
            cloud_percentage=cloud_percentage
        ),
        vegetation=VegetationStats(
            mean_ndvi=veg_stats["mean_ndvi"],
            minimum_ndvi=veg_stats["minimum_ndvi"],
            maximum_ndvi=veg_stats["maximum_ndvi"],
            valid_pixel_percentage=veg_stats["valid_pixel_percentage"]
        ),
        stress=StressStats(
            level=overall_level,
            classification_label="Potential vegetation stress",
            total_area_hectares=total_area_ha,
            stressed_area_hectares=stressed_ha,
            stressed_area_percentage=stressed_pct,
            baseline_mean_ndvi=baseline_info["baseline_mean_ndvi"],
            ndvi_change=baseline_info["ndvi_change"],
            ndvi_change_percentage=baseline_info["ndvi_change_percentage"]
        ),
        affected_zone=GeoJSONFeatureCollection(**fc_dict),
        outputs=outputs
    )

    # 10. Also acquire Sentinel-1 data if available and build standardized JSON output
    s1_data = None
    try:
        s1_service = Sentinel1Service()
        s1_data = s1_service.search_and_download(
            polygon=farm_poly,
            start_date=start_dt_str,
            end_date=end_dt_str
        )
    except Exception as s1_exc:
        logger.warning(f"Sentinel-1 SAR acquisition failed: {s1_exc}")

    try:
        std_output = build_standardized_output(
            zone_id=request.field_id,
            polygon=farm_poly,
            s2_data=data,
            s1_data=s1_data,
            valid_mask=valid_mask
        )
        save_standardized_json(std_output, request.field_id)
    except Exception as std_exc:
        logger.warning(f"Could not save standardized JSON output artifact: {std_exc}")

    # Cache response for GET /result/{field_id}
    RECENT_RESULTS[request.field_id] = response.model_dump()
    return response


@router.post(
    "/api/satellite/standardized",
    response_model=StandardizedSatelliteOutput,
    summary="Generate Standardized Machine-Readable Satellite Output JSON (Version 1.0)",
    status_code=status.HTTP_200_OK
)
def get_standardized_satellite_output(request: SatelliteAnalysisRequest):
    """Executes observation processing and returns standardized 1.0 JSON format:

    Combines:
    - Zone & EPSG:4326 polygon coordinates + Grid ID (10m resolution)
    - Observation acquisition timestamps
    - Sentinel-2 multispectral metrics (NDVI + NDWI 4-metric stats)
    - Sentinel-1 SAR metrics (VV + VH 3-metric backscatter stats in dB)
    - Data quality and independent satellite availability flags
    - Copernicus / Sentinel Hub processing metadata
    """
    try:
        farm_poly = parse_polygon_input(polygon_input=request.polygon, bbox_input=request.bbox)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid boundary: {str(val_err)}")

    start_dt_str = str(request.start_date)
    end_dt_str = str(request.end_date)
    if start_dt_str > end_dt_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be <= end_date")

    # 1. Acquire Sentinel-2 data
    s2_data = None
    valid_mask = None
    try:
        s2_service = Sentinel2Service()
        s2_data = s2_service.search_and_download(
            polygon=farm_poly,
            start_date=start_dt_str,
            end_date=end_dt_str,
            max_cloud_cover=request.max_cloud_cover
        )
        height, width = s2_data["ndvi"].shape
        farm_mask = _rasterize_farm_mask(farm_poly, height, width)
        valid_mask = apply_scl_cloud_mask(s2_data["scl"], s2_data["datamask"], farm_mask=farm_mask)
    except (NoSatelliteImageFoundError, CloudCoverExceededError) as s2_err:
        logger.info(f"Sentinel-2 unavailable for request: {s2_err}")
    except Exception as s2_exc:
        logger.warning(f"Sentinel-2 processing warning: {s2_exc}")

    # 2. Acquire Sentinel-1 data
    s1_data = None
    try:
        s1_service = Sentinel1Service()
        s1_data = s1_service.search_and_download(
            polygon=farm_poly,
            start_date=start_dt_str,
            end_date=end_dt_str
        )
    except Exception as s1_exc:
        logger.info(f"Sentinel-1 unavailable for request: {s1_exc}")

    std_output = build_standardized_output(
        zone_id=request.field_id,
        polygon=farm_poly,
        s2_data=s2_data,
        s1_data=s1_data,
        valid_mask=valid_mask
    )

    save_standardized_json(std_output, request.field_id)
    return std_output


@router.get(
    "/api/satellite/result/{field_id}",
    response_model=SatelliteAnalysisResponse,
    summary="Get most recent analysis result for a field"
)
def get_field_result(field_id: str):
    """Retrieve the most recent satellite analysis results computed for the given field ID."""
    if field_id not in RECENT_RESULTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recent satellite analysis found for field_id '{field_id}'. Please run /api/satellite/analyze first."
        )
    return RECENT_RESULTS[field_id]


@router.post(
    "/api/satellite/ndvi",
    summary="Compute NDVI only for a field"
)
def compute_ndvi_only(request: NDVIRequest):
    """Fast lightweight endpoint computing NDVI and vegetation stats without generating full maps."""
    try:
        farm_poly = parse_polygon_input(polygon_input=request.polygon, bbox_input=request.bbox)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    service = Sentinel2Service()
    try:
        data = service.search_and_download(
            polygon=farm_poly,
            start_date=str(request.start_date),
            end_date=str(request.end_date),
            max_cloud_cover=request.max_cloud_cover
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    ndvi = data["ndvi"]
    height, width = ndvi.shape
    farm_mask = _rasterize_farm_mask(farm_poly, height, width)
    valid_mask = apply_scl_cloud_mask(data["scl"], data["datamask"], farm_mask=farm_mask)
    stats = compute_vegetation_statistics(ndvi, valid_mask)

    return {
        "field_id": request.field_id,
        "image_date": data["image_date"],
        "cloud_percentage": data["cloud_percentage"],
        "is_simulated": data["is_simulated"],
        "vegetation": stats
    }

