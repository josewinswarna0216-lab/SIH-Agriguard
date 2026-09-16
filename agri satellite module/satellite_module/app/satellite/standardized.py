"""Standardized Satellite Output Generator and Artifact Writer.

Assembles Sentinel-2, Sentinel-1, geospatial grid, data quality, and availability
metadata into the standardized 1.0 JSON format.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from shapely.geometry import Polygon

from ..config import settings, OUTPUTS_DIR
from ..analysis.ndvi import compute_index_stats_4, compute_radar_stats_3
from ..models.standardized_schema import (
    StandardizedSatelliteOutput,
    ZoneInfo,
    ZoneCoordinates,
    GridInfo,
    ObservationInfo,
    Sentinel2Data,
    Sentinel1Data,
    AvailabilityInfo,
    ProcessingInfo,
    IndexStats4,
    RadarStats3
)

logger = logging.getLogger(__name__)


def build_standardized_output(
    zone_id: str,
    polygon: Polygon,
    s2_data: Optional[Dict[str, Any]] = None,
    s1_data: Optional[Dict[str, Any]] = None,
    valid_mask: Optional[Any] = None
) -> StandardizedSatelliteOutput:
    """Build standardized satellite observation payload conforming to Schema 1.0.

    Args:
        zone_id: Unique farm zone identifier (e.g. FARM01-ZONE03 or FIELD_001).
        polygon: Field boundary Shapely polygon in EPSG:4326.
        s2_data: Sentinel-2 search & raster download dictionary, or None if unavailable.
        s1_data: Sentinel-1 SAR dictionary, or None if unavailable.
        valid_mask: 2D boolean mask indicating valid non-cloud farm pixels.

    Returns:
        StandardizedSatelliteOutput model object.
    """
    min_lon, min_lat, max_lon, max_lat = polygon.bounds

    # 1. Zone & Coordinates
    exterior_ring = [[round(float(c[0]), 6), round(float(c[1]), 6)] for c in polygon.exterior.coords]
    coords_rings = [exterior_ring]
    for interior in polygon.interiors:
        coords_rings.append([[round(float(c[0]), 6), round(float(c[1]), 6)] for c in interior.coords])

    centroid = polygon.centroid
    lat_bin = abs(int(round(centroid.y * 100))) % 100
    lon_bin = abs(int(round(centroid.x * 100))) % 100
    grid_id = f"GRID_{lat_bin:02d}_{lon_bin:02d}"

    zone_info = ZoneInfo(
        zone_id=zone_id,
        coordinates=ZoneCoordinates(
            type="Polygon",
            coordinates=coords_rings,
            bbox=[round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)],
            crs="EPSG:4326"
        ),
        grid=GridInfo(
            grid_id=grid_id,
            resolution_m=10
        )
    )

    # 2. Sentinel-2 details
    s2_avail = s2_data is not None and s2_data.get("available", True) and s2_data.get("ndvi") is not None
    cloud_pct = s2_data.get("cloud_percentage") if s2_avail else None
    s2_quality = "UNAVAILABLE"
    ndvi_stats = None
    ndwi_stats = None

    if s2_avail:
        ndvi_array = s2_data["ndvi"]
        ndwi_array = s2_data.get("ndwi")
        s2_ndvi_dict = compute_index_stats_4(ndvi_array, valid_mask)
        ndvi_stats = IndexStats4(**s2_ndvi_dict)

        if ndwi_array is not None:
            s2_ndwi_dict = compute_index_stats_4(ndwi_array, valid_mask)
            ndwi_stats = IndexStats4(**s2_ndwi_dict)

        # Quality evaluation
        valid_pixel_pct = 100.0
        if valid_mask is not None and valid_mask.size > 0:
            valid_pixel_pct = (valid_mask.sum() / valid_mask.size) * 100.0

        if cloud_pct is not None and cloud_pct <= 10.0 and valid_pixel_pct >= 80.0:
            s2_quality = "GOOD"
        elif cloud_pct is not None and cloud_pct <= 20.0 and valid_pixel_pct >= 50.0:
            s2_quality = "MODERATE"
        elif valid_pixel_pct == 0.0:
            s2_quality = "INSUFFICIENT_DATA"
        else:
            s2_quality = "POOR"

    s2_payload = Sentinel2Data(
        available=s2_avail,
        cloud_coverage_percent=round(float(cloud_pct), 2) if cloud_pct is not None else None,
        data_quality=s2_quality,
        ndvi=ndvi_stats,
        ndwi=ndwi_stats
    )

    # 3. Sentinel-1 details
    s1_avail = s1_data is not None and s1_data.get("available", False)
    s1_quality = "UNAVAILABLE"
    vv_stats = None
    vh_stats = None

    if s1_avail:
        vv_array = s1_data.get("vv")
        vh_array = s1_data.get("vh")
        if vv_array is not None:
            vv_stats = RadarStats3(**compute_radar_stats_3(vv_array, valid_mask))
        if vh_array is not None:
            vh_stats = RadarStats3(**compute_radar_stats_3(vh_array, valid_mask))
        s1_quality = s1_data.get("data_quality", "GOOD")

    s1_payload = Sentinel1Data(
        available=s1_avail,
        timestamp=s1_data.get("timestamp") if s1_avail else None,
        orbit_direction=s1_data.get("orbit_direction") if s1_avail else None,
        polarization=s1_data.get("polarization") if s1_avail else None,
        vv=vv_stats,
        vh=vh_stats,
        data_quality=s1_quality
    )

    # 4. Primary observation metadata
    obs_timestamp = None
    obs_date = None
    obs_sat = None
    obs_platform = None
    obs_tile = None

    if s2_avail:
        obs_date = s2_data.get("image_date")
        obs_timestamp = s2_data.get("timestamp", f"{obs_date}T05:32:18Z" if obs_date else None)
        obs_sat = "Sentinel-2"
        obs_platform = s2_data.get("platform", "Sentinel-2A")
        obs_tile = s2_data.get("tile_id", "T44PKR")
    elif s1_avail:
        obs_timestamp = s1_data.get("timestamp")
        obs_date = obs_timestamp[:10] if obs_timestamp else None
        obs_sat = "Sentinel-1"
        obs_platform = "Sentinel-1A"

    observation_info = ObservationInfo(
        timestamp=obs_timestamp,
        date=obs_date,
        satellite=obs_sat,
        platform=obs_platform,
        tile_id=obs_tile
    )

    # 5. Availability summary
    cloud_free = s2_avail and (cloud_pct is not None and cloud_pct <= 15.0)

    overall_quality = "UNAVAILABLE"
    if s2_quality == "GOOD" and (not s1_avail or s1_quality == "GOOD"):
        overall_quality = "GOOD"
    elif s2_quality in ["GOOD", "MODERATE"] or s1_quality == "GOOD":
        overall_quality = "MODERATE"
    elif s2_avail or s1_avail:
        overall_quality = "POOR"

    availability_info = AvailabilityInfo(
        sentinel_2_available=s2_avail,
        sentinel_1_available=s1_avail,
        cloud_free=cloud_free,
        quality=overall_quality
    )

    # 6. Processing metadata
    processing_info = ProcessingInfo(
        source="Copernicus Data Space Ecosystem",
        api="Sentinel Hub Process API",
        processing_timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    output = StandardizedSatelliteOutput(
        schema_version="1.0",
        zone=zone_info,
        observation=observation_info,
        sentinel_2=s2_payload,
        sentinel_1=s1_payload,
        availability=availability_info,
        processing=processing_info
    )

    return output


def save_standardized_json(
    output: StandardizedSatelliteOutput,
    zone_id: str,
    output_dir: Optional[Path] = None
) -> Path:
    """Save standardized JSON model to output directory.

    Writes:
    1. outputs/satellite_observation.json (default integration file)
    2. outputs/{zone_id}.json (zone-specific integration file)

    Args:
        output: StandardizedSatelliteOutput instance.
        zone_id: Farm zone identifier.
        output_dir: Target outputs directory.

    Returns:
        Path to the primary saved JSON file.
    """
    out_dir = output_dir or settings.OUTPUT_PATH
    out_dir.mkdir(parents=True, exist_ok=True)

    data_dict = output.model_dump()

    # 1. Primary satellite_observation.json
    primary_path = out_dir / "satellite_observation.json"
    with open(primary_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=2)

    # 2. Zone-specific JSON (clean filename)
    safe_zone_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in zone_id)
    zone_path = out_dir / f"{safe_zone_id}.json"
    with open(zone_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=2)

    logger.info(f"Saved standardized satellite JSON to {primary_path} and {zone_path}")
    return primary_path
