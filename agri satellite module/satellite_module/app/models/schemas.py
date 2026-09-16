"""Pydantic schemas for request validation and response serialization."""

from datetime import date
from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon specification according to RFC 7946."""
    type: Literal["Polygon"] = Field(default="Polygon", description="Geometry type")
    coordinates: List[List[List[float]]] = Field(
        ...,
        description="Coordinates array: outer ring and optional interior rings. Each point is [longitude, latitude].",
        examples=[
            [
                [
                    [80.123, 13.012],
                    [80.128, 13.012],
                    [80.128, 13.018],
                    [80.123, 13.018],
                    [80.123, 13.012]
                ]
            ]
        ]
    )

    @field_validator("coordinates")
    @classmethod
    def validate_polygon_coords(cls, coords: List[List[List[float]]]) -> List[List[List[float]]]:
        if not coords or len(coords) < 1:
            raise ValueError("Polygon must have at least an exterior ring.")
        exterior = coords[0]
        if len(exterior) < 4:
            raise ValueError("Exterior ring must have at least 4 coordinate pairs (first and last matching).")
        # Check closed ring
        if exterior[0] != exterior[-1]:
            # Auto-close if first and last differ slightly or user forgot to repeat initial coordinate
            exterior.append(exterior[0])
        return coords


class GeoJSONFeatureProperties(BaseModel):
    """Properties associated with a detected high-stress zone."""
    stress_level: Literal["HIGH", "MODERATE", "HEALTHY"] = Field(
        default="HIGH",
        description="Stress classification level"
    )
    mean_ndvi: float = Field(..., description="Mean NDVI within this specific zone")
    area_hectares: float = Field(..., description="Calculated area of this zone in hectares")


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature for an affected zone."""
    type: Literal["Feature"] = "Feature"
    properties: GeoJSONFeatureProperties
    geometry: GeoJSONPolygon


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection containing all detected high-stress zones."""
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)


class SatelliteAnalysisRequest(BaseModel):
    """Request model for the full satellite analysis pipeline."""
    field_id: str = Field(..., description="Unique identifier for the farm field", examples=["FIELD_001"])
    polygon: Optional[GeoJSONPolygon] = Field(
        default=None,
        description="GeoJSON Polygon boundary of the farm in EPSG:4326 (WGS84)"
    )
    bbox: Optional[List[float]] = Field(
        default=None,
        description="Optional simple bounding box [min_lon, min_lat, max_lon, max_lat] for testing",
        examples=[[80.123, 13.012, 80.128, 13.018]]
    )
    start_date: Union[date, str] = Field(..., description="Search start date (YYYY-MM-DD)", examples=["2026-08-15"])
    end_date: Union[date, str] = Field(..., description="Search end date (YYYY-MM-DD)", examples=["2026-09-14"])
    crop: Optional[str] = Field(default="unknown", description="Crop type grown in this field", examples=["potato"])

    # Optional historical baseline comparison
    baseline_start_date: Optional[Union[date, str]] = Field(
        default=None,
        description="Optional historical baseline search start date (YYYY-MM-DD)"
    )
    baseline_end_date: Optional[Union[date, str]] = Field(
        default=None,
        description="Optional historical baseline search end date (YYYY-MM-DD)"
    )

    # Config overrides
    max_cloud_cover: Optional[float] = Field(
        default=None,
        description="Optional override for maximum cloud cover percentage threshold (0-100)"
    )

    @model_validator(mode="after")
    def check_boundary_input(self) -> "SatelliteAnalysisRequest":
        if self.polygon is None and self.bbox is None:
            raise ValueError("Either 'polygon' or 'bbox' must be provided.")
        if self.bbox is not None:
            if len(self.bbox) != 4:
                raise ValueError("bbox must contain exactly 4 numbers: [min_lon, min_lat, max_lon, max_lat]")
            min_lon, min_lat, max_lon, max_lat = self.bbox
            if min_lon >= max_lon or min_lat >= max_lat:
                raise ValueError("Invalid bbox bounds: min_lon < max_lon and min_lat < max_lat required.")
        return self


class NDVIRequest(BaseModel):
    """Request model for NDVI-only calculation."""
    field_id: str = Field(..., description="Unique field identifier", examples=["FIELD_001"])
    polygon: Optional[GeoJSONPolygon] = None
    bbox: Optional[List[float]] = None
    start_date: Union[date, str] = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: Union[date, str] = Field(..., description="End date (YYYY-MM-DD)")
    max_cloud_cover: Optional[float] = None


class SatelliteInfo(BaseModel):
    """Metadata about the selected satellite acquisition."""
    source: str = Field(default="Sentinel-2", description="Satellite constellation")
    processing_level: str = Field(default="L2A", description="Atmospheric correction level (Bottom-of-Atmosphere)")
    image_date: str = Field(..., description="Acquisition date of the selected scene (YYYY-MM-DD)")
    cloud_percentage: float = Field(..., description="Scene-level cloud cover percentage")


class VegetationStats(BaseModel):
    """Vegetation index statistics computed over valid non-cloud pixels."""
    mean_ndvi: float = Field(..., description="Mean NDVI value")
    minimum_ndvi: float = Field(..., description="Minimum NDVI value")
    maximum_ndvi: float = Field(..., description="Maximum NDVI value")
    valid_pixel_percentage: float = Field(..., description="Percentage of valid non-cloud farm pixels")


class StressStats(BaseModel):
    """Vegetation stress and anomaly detection metrics."""
    level: Literal["HEALTHY", "MODERATE", "HIGH"] = Field(
        ...,
        description="Overall field stress severity level"
    )
    classification_label: str = Field(
        default="Potential vegetation stress",
        description="Official classification label. Note: Satellite indicates anomaly/stress, not confirmed disease."
    )
    total_area_hectares: float = Field(..., description="Total farm area calculated in hectares")
    stressed_area_hectares: float = Field(..., description="High-stress area in hectares")
    stressed_area_percentage: float = Field(..., description="Percentage of farm area experiencing high stress")
    baseline_mean_ndvi: Optional[float] = Field(
        default=None,
        description="Historical baseline mean NDVI (if baseline was computed)"
    )
    ndvi_change: Optional[float] = Field(
        default=None,
        description="NDVI deviation from baseline (current_ndvi - baseline_ndvi)"
    )
    ndvi_change_percentage: Optional[float] = Field(
        default=None,
        description="Percentage NDVI deviation from baseline"
    )


class OutputFiles(BaseModel):
    """Locally generated map artifacts and GeoJSON file paths."""
    ndvi_map: str = Field(..., description="Relative URL or path to generated NDVI PNG map")
    stress_map: str = Field(..., description="Relative URL or path to generated stress classification PNG map")
    affected_geojson: Optional[str] = Field(
        default=None,
        description="Relative URL or path to affected zone GeoJSON"
    )


class SatelliteAnalysisResponse(BaseModel):
    """Complete response returned by the satellite analysis pipeline."""
    field_id: str
    crop: Optional[str]
    analysis_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of analysis execution")
    is_simulated: bool = Field(
        default=False,
        description="True if generated in DEMO_MODE using realistic simulated satellite data"
    )
    satellite: SatelliteInfo
    vegetation: VegetationStats
    stress: StressStats
    affected_zone: GeoJSONFeatureCollection
    outputs: OutputFiles


class HealthResponse(BaseModel):
    """API health status response."""
    status: str = "ok"
    version: str = "1.0.0"
    demo_mode: bool
    sentinelhub_configured: bool
