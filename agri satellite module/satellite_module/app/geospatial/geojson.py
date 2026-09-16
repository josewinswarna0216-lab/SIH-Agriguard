"""Vectorization of high-stress pixel regions into clean GeoJSON polygons.

Performs connected-component clustering, georeferenced coordinate transformation,
farm boundary clipping, and minimum-area noise filtering.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

from ..config import settings, OUTPUTS_DIR
from .area import calculate_polygon_area_hectares

logger = logging.getLogger(__name__)


def vectorize_mask_to_geojson(
    field_id: str,
    high_stress_mask: np.ndarray,
    ndvi: np.ndarray,
    farm_polygon: Polygon,
    min_area_hectares: Optional[float] = None,
    output_dir: Optional[Path] = None
) -> Tuple[Dict[str, Any], List[Polygon]]:
    """Convert connected high-stress pixels into clean, boundary-clipped GeoJSON polygons.

    Steps:
    1. Georeferencing: Map raster pixel indices (r, c) to geographic bounding boxes in EPSG:4326.
    2. Clustering / Union: Merge adjacent pixel boxes into contiguous polygons via unary_union.
    3. Clipping: Clip generated stress geometries strictly to the original farm boundary polygon.
    4. Noise Filtering: Discard isolated micro-polygons smaller than min_area_hectares.
    5. Geometry Cleaning: Apply make_valid and buffer(0) to ensure topological correctness.
    6. Feature Generation: Compute mean NDVI and area for each zone and format as GeoJSON.

    Args:
        field_id: Farm field ID for file naming.
        high_stress_mask: 2D boolean array (True = High Stress pixel).
        ndvi: 2D float array of NDVI values.
        farm_polygon: Shapely Polygon of the user's farm boundary.
        min_area_hectares: Minimum threshold to eliminate noise (default from config).
        output_dir: Directory where GeoJSON file is saved.

    Returns:
        Tuple:
            - Dict representing GeoJSON FeatureCollection
            - List of clipped Shapely Polygon objects
    """
    min_area = min_area_hectares if min_area_hectares is not None else settings.MIN_STRESS_AREA_HECTARES
    out_dir = output_dir or settings.OUTPUT_PATH
    out_dir.mkdir(parents=True, exist_ok=True)

    height, width = high_stress_mask.shape
    min_lon, min_lat, max_lon, max_lat = farm_polygon.bounds

    dx = (max_lon - min_lon) / width
    dy = (max_lat - min_lat) / height

    # 1. Create pixel boxes for all high-stress pixels
    active_rows, active_cols = np.where(high_stress_mask)
    if len(active_rows) == 0:
        empty_fc = {"type": "FeatureCollection", "features": []}
        _save_geojson_file(field_id, empty_fc, out_dir)
        return empty_fc, []

    pixel_boxes = []
    for r, c in zip(active_rows, active_cols):
        p_min_lon = min_lon + c * dx
        p_max_lon = min_lon + (c + 1) * dx
        p_max_lat = max_lat - r * dy
        p_min_lat = max_lat - (r + 1) * dy
        pixel_boxes.append(box(p_min_lon, p_min_lat, p_max_lon, p_max_lat))

    # 2. Merge adjacent pixel boxes into unified polygon(s)
    merged_geom = unary_union(pixel_boxes)

    # Decompose into single polygons
    raw_polygons: List[Polygon] = []
    if isinstance(merged_geom, Polygon):
        raw_polygons = [merged_geom]
    elif isinstance(merged_geom, MultiPolygon):
        raw_polygons = list(merged_geom.geoms)

    # 3. Clean, clip to farm polygon, and filter by minimum area
    valid_features = []
    clipped_polys: List[Polygon] = []

    for raw_poly in raw_polygons:
        # Clean geometry
        cleaned = make_valid(raw_poly)
        # Clip strictly to farm boundary
        clipped = cleaned.intersection(farm_polygon)

        sub_polys: List[Polygon] = []
        if isinstance(clipped, Polygon):
            sub_polys = [clipped]
        elif isinstance(clipped, MultiPolygon):
            sub_polys = list(clipped.geoms)

        for poly in sub_polys:
            if poly.is_empty or poly.area <= 0:
                continue

            # Check area in hectares
            poly_ha = calculate_polygon_area_hectares(poly)
            if poly_ha < min_area:
                logger.debug(f"Filtered out noise polygon with area {poly_ha:.4f} ha (< {min_area} ha)")
                continue

            # Estimate mean NDVI in this polygon zone
            zone_mean_ndvi = _calculate_polygon_mean_ndvi(poly, ndvi, min_lon, max_lat, dx, dy, width, height)

            # Round coordinates to 6 decimals (approx 10cm accuracy) for clean JSON
            geojson_geom = _format_polygon_coords(poly)

            feature = {
                "type": "Feature",
                "properties": {
                    "stress_level": "HIGH",
                    "mean_ndvi": round(float(zone_mean_ndvi), 2),
                    "area_hectares": round(float(poly_ha), 2)
                },
                "geometry": geojson_geom
            }

            valid_features.append(feature)
            clipped_polys.append(poly)

    feature_collection = {
        "type": "FeatureCollection",
        "features": valid_features
    }

    _save_geojson_file(field_id, feature_collection, out_dir)
    return feature_collection, clipped_polys


def _calculate_polygon_mean_ndvi(
    poly: Polygon,
    ndvi: np.ndarray,
    min_lon: float,
    max_lat: float,
    dx: float,
    dy: float,
    width: int,
    height: int
) -> float:
    """Sample raster pixels enclosed by or intersecting the polygon to compute mean NDVI."""
    p_min_lon, p_min_lat, p_max_lon, p_max_lat = poly.bounds

    c_start = max(0, int((p_min_lon - min_lon) / dx))
    c_end = min(width, int(np.ceil((p_max_lon - min_lon) / dx)))
    r_start = max(0, int((max_lat - p_max_lat) / dy))
    r_end = min(height, int(np.ceil((max_lat - p_min_lat) / dy)))

    sub_ndvi = ndvi[r_start:r_end, c_start:c_end]
    if sub_ndvi.size > 0:
        return float(np.mean(sub_ndvi))
    return 0.35


def _format_polygon_coords(poly: Polygon) -> Dict[str, Any]:
    """Format Shapely polygon coordinates with rounded float values for GeoJSON."""
    coords = []
    # Exterior ring
    exterior = [[round(float(c[0]), 6), round(float(c[1]), 6)] for c in poly.exterior.coords]
    coords.append(exterior)
    # Interior rings (holes)
    for interior in poly.interiors:
        hole = [[round(float(c[0]), 6), round(float(c[1]), 6)] for c in interior.coords]
        coords.append(hole)

    return {
        "type": "Polygon",
        "coordinates": coords
    }


def _save_geojson_file(field_id: str, feature_collection: Dict[str, Any], output_dir: Path) -> Path:
    """Save GeoJSON FeatureCollection locally to outputs directory."""
    filename = f"{field_id}_affected.geojson"
    filepath = output_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f, indent=2)
    return filepath
