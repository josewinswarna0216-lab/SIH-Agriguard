"""Geospatial polygon parsing, coordinate validation, and geometry conversion.

Converts GeoJSON Polygon inputs and bounding boxes into Shapely geometries
and Sentinel Hub BBox/Geometry structures.
"""

from typing import Union, List, Tuple, Optional, Dict, Any
from shapely.geometry import Polygon, box, mapping, shape
from shapely.validation import make_valid
from sentinelhub import BBox, Geometry, CRS

from ..models.schemas import GeoJSONPolygon


def validate_and_fix_coords(coords: List[List[float]]) -> List[List[float]]:
    """Validate coordinate pairs for WGS84 range and ensure the ring is closed.

    GeoJSON specifies [longitude, latitude].
    Longitude must be in [-180, 180], Latitude must be in [-90, 90].

    Args:
        coords: List of [lon, lat] coordinates for a ring.

    Returns:
        List[List[float]]: Validated and closed coordinates.

    Raises:
        ValueError: If coordinates are out of geographical range or improperly formatted.
    """
    if len(coords) < 3:
        raise ValueError(f"A polygon ring must contain at least 3 points, got {len(coords)}.")

    fixed_coords = []
    for idx, pt in enumerate(coords):
        if len(pt) != 2:
            raise ValueError(f"Coordinate at index {idx} must have [longitude, latitude], got: {pt}")
        lon, lat = float(pt[0]), float(pt[1])

        # Validate range
        if not (-180.0 <= lon <= 180.0):
            # Check if user reversed lat/lon (e.g. lon is outside 180 or looks like lat)
            raise ValueError(
                f"Longitude {lon} at coordinate index {idx} is out of bounds [-180, 180]. "
                f"Ensure GeoJSON order is [longitude, latitude]."
            )
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(
                f"Latitude {lat} at coordinate index {idx} is out of bounds [-90, 90]. "
                f"Ensure GeoJSON order is [longitude, latitude]."
            )
        fixed_coords.append([lon, lat])

    # Ensure closed ring
    if fixed_coords[0] != fixed_coords[-1]:
        fixed_coords.append(fixed_coords[0])

    return fixed_coords


def parse_polygon_input(
    polygon_input: Optional[Union[GeoJSONPolygon, Dict[str, Any], Polygon]] = None,
    bbox_input: Optional[List[float]] = None
) -> Polygon:
    """Parse incoming GeoJSON polygon or bounding box into a valid Shapely Polygon.

    Args:
        polygon_input: GeoJSON Polygon model, dict, or Shapely Polygon.
        bbox_input: Optional bounding box [min_lon, min_lat, max_lon, max_lat].

    Returns:
        Polygon: Validated Shapely Polygon in WGS84 (EPSG:4326).

    Raises:
        ValueError: If neither or invalid inputs are supplied.
    """
    if bbox_input is not None:
        if len(bbox_input) != 4:
            raise ValueError("Bounding box must contain [min_lon, min_lat, max_lon, max_lat].")
        min_lon, min_lat, max_lon, max_lat = map(float, bbox_input)
        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError(
                f"Invalid bounding box: min_lon ({min_lon}) must be < max_lon ({max_lon}) "
                f"and min_lat ({min_lat}) must be < max_lat ({max_lat})."
            )
        # Check geographic limits
        for lon in (min_lon, max_lon):
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Longitude {lon} in bbox is out of bounds [-180, 180].")
        for lat in (min_lat, max_lat):
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude {lat} in bbox is out of bounds [-90, 90].")
        return box(min_lon, min_lat, max_lon, max_lat)

    if polygon_input is None:
        raise ValueError("Either polygon or bbox must be provided.")

    if isinstance(polygon_input, Polygon):
        poly = polygon_input
    elif isinstance(polygon_input, GeoJSONPolygon):
        rings = [validate_and_fix_coords(ring) for ring in polygon_input.coordinates]
        poly = Polygon(rings[0], rings[1:] if len(rings) > 1 else None)
    elif isinstance(polygon_input, dict):
        if polygon_input.get("type") == "Polygon" and "coordinates" in polygon_input:
            raw_rings = polygon_input["coordinates"]
            rings = [validate_and_fix_coords(ring) for ring in raw_rings]
            poly = Polygon(rings[0], rings[1:] if len(rings) > 1 else None)
        else:
            # Try generic shape parser
            poly = shape(polygon_input)
            if not isinstance(poly, Polygon):
                raise ValueError(f"Expected Polygon geometry, but got: {poly.geom_type}")
    else:
        raise ValueError(f"Unsupported polygon input type: {type(polygon_input)}")

    # Ensure validity
    if not poly.is_valid:
        poly = make_valid(poly)
        if poly.geom_type == "MultiPolygon":
            # Select largest polygon if split by self-intersection
            poly = max(poly.geoms, key=lambda a: a.area)

    if poly.is_empty or poly.area <= 0:
        raise ValueError("The provided polygon is empty or has zero surface area.")

    return poly


def polygon_to_sh_geometry(poly: Polygon) -> Geometry:
    """Convert a Shapely Polygon into a Sentinel Hub Geometry object with EPSG:4326.

    Args:
        poly: Shapely Polygon.

    Returns:
        Geometry: Sentinel Hub Geometry.
    """
    return Geometry(geometry=poly, crs=CRS.WGS84)


def get_polygon_bbox(poly: Polygon) -> BBox:
    """Get the Sentinel Hub BBox enclosing the Shapely Polygon.

    Args:
        poly: Shapely Polygon.

    Returns:
        BBox: Sentinel Hub BBox in WGS84.
    """
    min_lon, min_lat, max_lon, max_lat = poly.bounds
    return BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.WGS84)
