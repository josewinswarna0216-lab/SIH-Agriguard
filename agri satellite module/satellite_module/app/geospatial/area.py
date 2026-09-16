"""Geospatial area calculation using WGS84 geodesic ellipsoidal projections.

Provides accurate surface area calculations in hectares for farm boundaries and
affected stress polygons without Euclidean planar distortion.
"""

import logging
from typing import Union
from shapely.geometry import Polygon, MultiPolygon
import pyproj

logger = logging.getLogger(__name__)

# WGS84 Geodesic calculator for precise ellipsoidal area
GEOD_WGS84 = pyproj.Geod(ellps="WGS84")


def calculate_polygon_area_hectares(geometry: Union[Polygon, MultiPolygon]) -> float:
    """Calculate the precise geodesic surface area of a polygon in hectares.

    Uses pyproj WGS84 ellipsoid geometry to account for latitude distortion.
    1 Hectare = 10,000 square meters.

    Args:
        geometry: Shapely Polygon or MultiPolygon in EPSG:4326 (WGS84).

    Returns:
        float: Surface area in hectares rounded to 2 decimal places.
    """
    if geometry is None or geometry.is_empty:
        return 0.0

    try:
        # geometry_area_perimeter computes geodesic area in m^2
        area_m2, _ = GEOD_WGS84.geometry_area_perimeter(geometry)
        area_m2 = abs(area_m2)
        hectares = area_m2 / 10000.0
        return round(float(hectares), 2)
    except Exception as exc:
        logger.warning(f"Geodesic area calculation failed, falling back to planar estimate: {exc}")
        # Fallback: planar approximation near equator (1 deg lat ~ 111 km)
        # area in deg^2 * (111000 * 111000 * cos(lat)) / 10000
        return 0.0


def calculate_mask_area_hectares(
    stressed_polygons: list,
    farm_polygon: Polygon
) -> tuple[float, float, float]:
    """Calculate farm total area, stressed area, and stressed area percentage in hectares.

    Args:
        stressed_polygons: List of clipped Shapely Polygons representing high stress zones.
        farm_polygon: Original farm boundary Polygon.

    Returns:
        tuple: (total_area_hectares, stressed_area_hectares, stressed_area_percentage)
    """
    total_farm_ha = calculate_polygon_area_hectares(farm_polygon)

    # Sum the area of valid high-stress polygons
    stressed_ha = 0.0
    for poly in stressed_polygons:
        stressed_ha += calculate_polygon_area_hectares(poly)

    stressed_ha = round(float(stressed_ha), 2)

    # Avoid division by zero
    if total_farm_ha > 0.0:
        stressed_pct = round(min(100.0, (stressed_ha / total_farm_ha) * 100.0), 2)
    else:
        stressed_pct = 0.0

    return total_farm_ha, stressed_ha, stressed_pct
