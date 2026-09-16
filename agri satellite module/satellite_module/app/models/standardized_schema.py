"""Standardized Satellite Output Schema (Version 1.0)

Defines Pydantic models conforming to the standardized machine-readable JSON format
for downstream agricultural disease early-warning integration.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class GridInfo(BaseModel):
    """Spatial grid parameters for the farm zone."""
    grid_id: str = Field(..., description="Unique spatial grid bin identifier", examples=["GRID_03_12"])
    resolution_m: int = Field(default=10, description="Spatial resolution in meters")


class ZoneCoordinates(BaseModel):
    """Geographic zone coordinates and bounding box in EPSG:4326."""
    type: Literal["Polygon"] = Field(default="Polygon", description="GeoJSON geometry type")
    coordinates: List[List[List[float]]] = Field(..., description="GeoJSON polygon coordinate rings")
    bbox: List[float] = Field(..., description="Bounding box [min_lon, min_lat, max_lon, max_lat]")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System")


class ZoneInfo(BaseModel):
    """Farm zone identification and boundary geometry."""
    zone_id: str = Field(..., description="Farm zone identifier", examples=["FARM01-ZONE03"])
    coordinates: ZoneCoordinates
    grid: GridInfo


class ObservationInfo(BaseModel):
    """Primary satellite observation metadata."""
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 acquisition timestamp", examples=["2026-09-15T05:32:18Z"])
    date: Optional[str] = Field(default=None, description="Acquisition date (YYYY-MM-DD)", examples=["2026-09-15"])
    satellite: Optional[str] = Field(default="Sentinel-2", description="Satellite constellation name")
    platform: Optional[str] = Field(default=None, description="Satellite platform identifier", examples=["Sentinel-2A"])
    tile_id: Optional[str] = Field(default=None, description="Granule / Tile ID", examples=["T44PKR"])


class IndexStats4(BaseModel):
    """4-metric statistics for spectral vegetation indices (mean, min, max, std)."""
    mean: Optional[float] = Field(default=None, description="Mean index value")
    min: Optional[float] = Field(default=None, description="Minimum index value")
    max: Optional[float] = Field(default=None, description="Maximum index value")
    std: Optional[float] = Field(default=None, description="Standard deviation")


class RadarStats3(BaseModel):
    """3-metric statistics for synthetic aperture radar backscatter (mean, min, max)."""
    mean: Optional[float] = Field(default=None, description="Mean backscatter value in dB")
    min: Optional[float] = Field(default=None, description="Minimum backscatter value in dB")
    max: Optional[float] = Field(default=None, description="Maximum backscatter value in dB")


class Sentinel2Data(BaseModel):
    """Sentinel-2 optical multispectral observation parameters and vegetation indices."""
    available: bool = Field(..., description="Whether Sentinel-2 data is available for this observation")
    cloud_coverage_percent: Optional[float] = Field(default=None, description="Scene cloud coverage percentage")
    data_quality: str = Field(default="UNAVAILABLE", description="Quality indicator: GOOD, MODERATE, POOR, INSUFFICIENT_DATA, UNAVAILABLE")
    ndvi: Optional[IndexStats4] = Field(default=None, description="Normalized Difference Vegetation Index statistics")
    ndwi: Optional[IndexStats4] = Field(default=None, description="Normalized Difference Water Index statistics")


class Sentinel1Data(BaseModel):
    """Sentinel-1 Synthetic Aperture Radar (SAR) backscatter parameters."""
    available: bool = Field(..., description="Whether Sentinel-1 SAR data is available for this observation")
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 SAR acquisition timestamp")
    orbit_direction: Optional[str] = Field(default=None, description="Orbit direction: ASCENDING, DESCENDING, or null")
    polarization: Optional[List[str]] = Field(default=None, description="Radar polarization modes, e.g., ['VV', 'VH']")
    vv: Optional[RadarStats3] = Field(default=None, description="VV polarization backscatter statistics (dB)")
    vh: Optional[RadarStats3] = Field(default=None, description="VH polarization backscatter statistics (dB)")
    data_quality: str = Field(default="UNAVAILABLE", description="Quality indicator: GOOD, MODERATE, POOR, INSUFFICIENT_DATA, UNAVAILABLE")


class AvailabilityInfo(BaseModel):
    """Overall satellite data availability and quality flags."""
    sentinel_2_available: bool = Field(..., description="True if Sentinel-2 data is available")
    sentinel_1_available: bool = Field(..., description="True if Sentinel-1 data is available")
    cloud_free: bool = Field(..., description="True if Sentinel-2 observation is clear of excessive cloud cover")
    quality: str = Field(..., description="Overall observation quality: GOOD, MODERATE, POOR, INSUFFICIENT_DATA, UNAVAILABLE")


class ProcessingInfo(BaseModel):
    """Data processing source and execution metadata."""
    source: str = Field(default="Copernicus Data Space Ecosystem", description="Satellite data provider source")
    api: str = Field(default="Sentinel Hub Process API", description="Processing API endpoint")
    processing_timestamp: str = Field(..., description="ISO 8601 timestamp of data processing execution")


class StandardizedSatelliteOutput(BaseModel):
    """Root standardized machine-readable JSON model for agricultural satellite observations."""
    schema_version: str = Field(default="1.0", description="Schema version specification")
    zone: ZoneInfo
    observation: ObservationInfo
    sentinel_2: Sentinel2Data
    sentinel_1: Sentinel1Data
    availability: AvailabilityInfo
    processing: ProcessingInfo
