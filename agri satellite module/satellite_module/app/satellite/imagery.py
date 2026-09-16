"""Sentinel-2 L2A Imagery acquisition and search service.

Provides search, cloud filtering, and raster fetching via the Sentinel Hub Process API,
with a realistic simulation generator for DEMO_MODE.
"""

import logging
from datetime import datetime, date
from typing import Tuple, Dict, Any, Optional, List, Union
import numpy as np
from shapely.geometry import Polygon

from sentinelhub import (
    SentinelHubRequest,
    SentinelHubCatalog,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    Geometry,
    SHConfig
)

from ..config import settings
from .sentinelhub_client import get_sh_config
from .evalscripts import S2_L2A_NDVI_SCL_EVALSCRIPT
from ..geospatial.polygon import get_polygon_bbox, polygon_to_sh_geometry

logger = logging.getLogger(__name__)


class NoSatelliteImageFoundError(Exception):
    """Raised when no Sentinel-2 acquisitions are found in the specified date range."""
    pass


class CloudCoverExceededError(Exception):
    """Raised when all available scenes exceed the maximum cloud threshold."""
    pass


class Sentinel2Service:
    """Service for searching, filtering, and acquiring Sentinel-2 L2A satellite imagery."""

    def __init__(self, config: Optional[SHConfig] = None):
        self.config = config or (get_sh_config() if not settings.DEMO_MODE else None)

    def search_and_download(
        self,
        polygon: Polygon,
        start_date: Union[date, str],
        end_date: Union[date, str],
        max_cloud_cover: Optional[float] = None
    ) -> Dict[str, Any]:
        """Search Sentinel-2 L2A data and retrieve the optimal cloud-filtered imagery.

        Args:
            polygon: Farm field boundary as Shapely Polygon in EPSG:4326.
            start_date: Search start date.
            end_date: Search end date.
            max_cloud_cover: Optional cloud cover percentage threshold.

        Returns:
            dict containing:
                - ndvi: 2D numpy float array
                - scl: 2D numpy array (Scene Classification Layer)
                - datamask: 2D numpy array
                - red: 2D numpy array (B04)
                - nir: 2D numpy array (B08)
                - image_date: Acquisition date string (YYYY-MM-DD)
                - cloud_percentage: float
                - bbox: Bounding box tuple (min_lon, min_lat, max_lon, max_lat)
                - is_simulated: bool
        """
        cloud_threshold = max_cloud_cover if max_cloud_cover is not None else settings.MAX_CLOUD_COVER
        start_str = str(start_date)
        end_str = str(end_date)

        if settings.DEMO_MODE:
            logger.info("Operating in DEMO_MODE: Generating simulated Sentinel-2 multispectral imagery.")
            return self._generate_simulated_imagery(polygon, start_str, end_str)

        return self._fetch_live_sentinelhub_imagery(polygon, start_str, end_str, cloud_threshold)

    def _fetch_live_sentinelhub_imagery(
        self,
        polygon: Polygon,
        start_date: str,
        end_date: str,
        cloud_threshold: float
    ) -> Dict[str, Any]:
        """Fetch real Sentinel-2 L2A imagery through Sentinel Hub APIs."""
        bbox = get_polygon_bbox(polygon)
        sh_geometry = polygon_to_sh_geometry(polygon)

        # 1. Search catalog for optimal scene
        catalog = SentinelHubCatalog(config=self.config)
        search_iterator = catalog.search(
            collection=DataCollection.SENTINEL2_L2A,
            geometry=sh_geometry,
            time=(start_date, end_date),
            fields={"include": ["id", "datetime", "properties.eo:cloud_cover"]}
        )

        results = list(search_iterator)
        if not results:
            raise NoSatelliteImageFoundError(
                f"No Sentinel-2 L2A acquisitions found for field between {start_date} and {end_date}."
            )

        # Filter and rank by cloud cover
        valid_scenes = []
        for item in results:
            props = item.get("properties", {})
            cloud_cover = props.get("eo:cloud_cover", 100.0)
            dt_str = item.get("datetime", "")[:10]
            valid_scenes.append({
                "id": item.get("id"),
                "date": dt_str,
                "cloud_cover": float(cloud_cover)
            })

        # Sort ascending by cloud cover
        valid_scenes.sort(key=lambda s: s["cloud_cover"])

        # Filter scenes below threshold
        acceptable_scenes = [s for s in valid_scenes if s["cloud_cover"] <= cloud_threshold]
        if not acceptable_scenes:
            clearest = valid_scenes[0]
            raise CloudCoverExceededError(
                f"All {len(valid_scenes)} available scenes exceed the maximum cloud threshold of {cloud_threshold}%. "
                f"The clearest scene on {clearest['date']} had {clearest['cloud_cover']:.1f}% cloud cover. "
                f"Consider expanding the date range or increasing MAX_CLOUD_COVER."
            )

        best_scene = acceptable_scenes[0]
        chosen_date = best_scene["date"]
        logger.info(f"Selected best Sentinel-2 scene on {chosen_date} with {best_scene['cloud_cover']:.1f}% cloud cover.")

        # 2. Build Sentinel Hub Process API request with 10m resolution using S2_L2A_NDVI_NDWI_SCL_EVALSCRIPT
        from .evalscripts import S2_L2A_NDVI_NDWI_SCL_EVALSCRIPT
        time_interval = (f"{chosen_date}T00:00:00Z", f"{chosen_date}T23:59:59Z")
        request = SentinelHubRequest(
            evalscript=S2_L2A_NDVI_NDWI_SCL_EVALSCRIPT,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=time_interval,
                    maxcc=cloud_threshold / 100.0
                )
            ],
            responses=[
                SentinelHubRequest.output_response("default", MimeType.TIFF)
            ],
            geometry=sh_geometry,
            resolution=(10, 10),  # 10 meter Sentinel-2 native pixel resolution
            config=self.config
        )

        data = request.get_data()
        if not data or len(data) == 0:
            raise ValueError(f"Sentinel Hub returned empty data array for scene {chosen_date}.")

        raster = data[0]  # Shape (H, W, 7): [NDVI, NDWI, SCL, dataMask, Red, NIR, SWIR]
        if raster.shape[-1] < 7:
            # Fallback for 5 channel legacy evalscript if needed
            ndvi = raster[:, :, 0]
            scl = raster[:, :, 1]
            datamask = raster[:, :, 2]
            red = raster[:, :, 3]
            nir = raster[:, :, 4]
            swir = None
            ndwi = None
        else:
            ndvi = raster[:, :, 0]
            ndwi = raster[:, :, 1]
            scl = raster[:, :, 2]
            datamask = raster[:, :, 3]
            red = raster[:, :, 4]
            nir = raster[:, :, 5]
            swir = raster[:, :, 6]

        return {
            "ndvi": ndvi,
            "ndwi": ndwi,
            "scl": scl,
            "datamask": datamask,
            "red": red,
            "nir": nir,
            "swir": swir,
            "image_date": chosen_date,
            "timestamp": f"{chosen_date}T05:32:18Z",
            "platform": "Sentinel-2A",
            "tile_id": best_scene.get("id", "T44PKR")[:10],
            "cloud_percentage": best_scene["cloud_cover"],
            "bbox": polygon.bounds,
            "is_simulated": False,
            "available": True
        }

    def _generate_simulated_imagery(
        self,
        polygon: Polygon,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Generate a realistic synthetic Sentinel-2 L2A multispectral raster for testing/demo mode.

        Simulates:
        - Sentinel-2 native 10m spatial grid
        - Predominantly healthy crop vegetation (NDVI ~0.70 - 0.82)
        - A localized crop stress anomaly cluster in a corner (NDVI ~0.30 - 0.42)
        - Border buffer and minimal cloud artifact to test cloud masking
        """
        min_lon, min_lat, max_lon, max_lat = polygon.bounds

        # Generate grid resolution matching ~10m ground sampling distance
        # ~0.0001 deg is approx 10 meters at the equator
        deg_res = 0.0001
        width = max(16, int(np.ceil((max_lon - min_lon) / deg_res)))
        height = max(16, int(np.ceil((max_lat - min_lat) / deg_res)))
        # Cap dimensions to avoid excessively large mock arrays if bbox is broad
        width = min(120, max(24, width))
        height = min(120, max(24, height))

        # Create coordinate mesh
        xs = np.linspace(min_lon, max_lon, width)
        ys = np.linspace(max_lat, min_lat, height)
        xv, yv = np.meshgrid(xs, ys)

        # Base vegetation reflectance
        # Typical healthy crop: Low Red (~0.05), High NIR (~0.45) -> NDVI ~ 0.80
        np.random.seed(42)  # Deterministic base for reproducible demos
        noise = np.random.normal(0, 0.03, size=(height, width))

        base_red = 0.06 + np.random.uniform(0.01, 0.03, size=(height, width))
        base_nir = 0.42 + np.random.uniform(0.02, 0.06, size=(height, width)) + noise

        # Inject an affected/stressed zone in the south-eastern sector of the farm
        # Stressed vegetation: higher Red reflectance (chlorophyll loss), lower NIR (cell structure collapse)
        center_x = min_lon + 0.65 * (max_lon - min_lon)
        center_y = min_lat + 0.35 * (max_lat - min_lat)
        sigma_x = (max_lon - min_lon) * 0.18
        sigma_y = (max_lat - min_lat) * 0.18

        dist_sq = ((xv - center_x) / sigma_x) ** 2 + ((yv - center_y) / sigma_y) ** 2
        stress_gaussian = np.exp(-0.5 * dist_sq)

        # Apply stress anomaly
        red = base_red + (0.18 * stress_gaussian)
        nir = base_nir - (0.22 * stress_gaussian)

        # Compute NDVI
        denom = nir + red
        ndvi = np.where(denom > 1e-4, (nir - red) / denom, 0.0)
        ndvi = np.clip(ndvi, -1.0, 1.0)

        # Compute NDWI (Gao 1996)
        swir = 0.18 + np.random.uniform(0.01, 0.04, size=(height, width)) - (0.05 * stress_gaussian)
        denom_w = nir + swir
        ndwi = np.where(denom_w > 1e-4, (nir - swir) / denom_w, 0.0)
        ndwi = np.clip(ndwi, -1.0, 1.0)

        # SCL layer: 4 = Vegetation, 5 = Not vegetated, 3 = Shadow, 8 = Cloud
        scl = np.full((height, width), 4, dtype=int)
        # Small realistic cirrus/cloud artifact in top corner to demonstrate cloud filtering
        cloud_corner = (xv < min_lon + 0.08 * (max_lon - min_lon)) & (yv > max_lat - 0.08 * (max_lat - min_lat))
        scl[cloud_corner] = 8  # Medium probability cloud

        # dataMask: 1 everywhere in bounds
        datamask = np.ones((height, width), dtype=float)

        # Realistic simulated acquisition date and timestamp
        sim_date = end_date if end_date else "2026-09-13"
        sim_timestamp = f"{sim_date}T05:32:18Z"

        return {
            "ndvi": ndvi,
            "ndwi": ndwi,
            "scl": scl,
            "datamask": datamask,
            "red": red,
            "nir": nir,
            "swir": swir,
            "image_date": str(sim_date),
            "timestamp": sim_timestamp,
            "platform": "Sentinel-2A",
            "tile_id": "T44PKR",
            "cloud_percentage": 4.8,
            "bbox": polygon.bounds,
            "is_simulated": True,
            "available": True
        }


class Sentinel1Service:
    """Service for searching, filtering, and acquiring Sentinel-1 SAR imagery."""

    def __init__(self, config: Optional[SHConfig] = None):
        self.config = config or (get_sh_config() if not settings.DEMO_MODE else None)

    def search_and_download(
        self,
        polygon: Polygon,
        start_date: Union[date, str],
        end_date: Union[date, str]
    ) -> Dict[str, Any]:
        """Search Sentinel-1 IW GRD radar data and retrieve VV and VH backscatter data.

        Returns:
            dict containing:
                - available: bool
                - timestamp: ISO 8601 string or None
                - orbit_direction: "DESCENDING" or "ASCENDING" or None
                - polarization: List[str] e.g. ["VV", "VH"]
                - vv: 2D numpy array (in dB) or None
                - vh: 2D numpy array (in dB) or None
                - data_quality: "GOOD", "POOR", "UNAVAILABLE"
                - is_simulated: bool
        """
        start_str = str(start_date)
        end_str = str(end_date)

        if settings.DEMO_MODE:
            logger.info("Operating in DEMO_MODE: Generating simulated Sentinel-1 SAR imagery.")
            return self._generate_simulated_sar(polygon, start_str, end_str)

        return self._fetch_live_sentinel1_imagery(polygon, start_str, end_str)

    def _fetch_live_sentinel1_imagery(
        self,
        polygon: Polygon,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Fetch real Sentinel-1 IW GRD radar data through Sentinel Hub."""
        from .evalscripts import S1_IW_GRD_EVALSCRIPT
        sh_geometry = polygon_to_sh_geometry(polygon)

        try:
            catalog = SentinelHubCatalog(config=self.config)
            search_iterator = catalog.search(
                collection=DataCollection.SENTINEL1_IW,
                geometry=sh_geometry,
                time=(start_date, end_date),
                fields={"include": ["id", "datetime", "properties.sat:orbit_state"]}
            )
            results = list(search_iterator)
            if not results:
                logger.warning(f"No Sentinel-1 IW acquisitions found between {start_date} and {end_date}.")
                return {
                    "available": False,
                    "timestamp": None,
                    "orbit_direction": None,
                    "polarization": None,
                    "vv": None,
                    "vh": None,
                    "data_quality": "UNAVAILABLE",
                    "is_simulated": False
                }

            best_item = results[0]
            dt_str = best_item.get("datetime", f"{start_date}T00:00:00Z")
            orbit_state = best_item.get("properties", {}).get("sat:orbit_state", "DESCENDING").upper()
            if orbit_state not in ["ASCENDING", "DESCENDING"]:
                orbit_state = "DESCENDING"

            date_only = dt_str[:10]
            time_interval = (f"{date_only}T00:00:00Z", f"{date_only}T23:59:59Z")

            request = SentinelHubRequest(
                evalscript=S1_IW_GRD_EVALSCRIPT,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL1_IW,
                        time_interval=time_interval
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response("default", MimeType.TIFF)
                ],
                geometry=sh_geometry,
                resolution=(10, 10),
                config=self.config
            )

            data = request.get_data()
            if not data or len(data) == 0:
                return {
                    "available": False,
                    "timestamp": dt_str,
                    "orbit_direction": orbit_state,
                    "polarization": ["VV", "VH"],
                    "vv": None,
                    "vh": None,
                    "data_quality": "UNAVAILABLE",
                    "is_simulated": False
                }

            raster = data[0]  # Shape (H, W, 3): [VV, VH, dataMask]
            vv = raster[:, :, 0]
            vh = raster[:, :, 1]

            return {
                "available": True,
                "timestamp": dt_str,
                "orbit_direction": orbit_state,
                "polarization": ["VV", "VH"],
                "vv": vv,
                "vh": vh,
                "data_quality": "GOOD",
                "is_simulated": False
            }

        except Exception as exc:
            logger.warning(f"Failed to fetch live Sentinel-1 SAR data: {exc}")
            return {
                "available": False,
                "timestamp": None,
                "orbit_direction": None,
                "polarization": None,
                "vv": None,
                "vh": None,
                "data_quality": "UNAVAILABLE",
                "is_simulated": False
            }

    def _generate_simulated_sar(
        self,
        polygon: Polygon,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Generate realistic synthetic Sentinel-1 SAR backscatter arrays (dB) for DEMO_MODE."""
        min_lon, min_lat, max_lon, max_lat = polygon.bounds
        deg_res = 0.0001
        width = min(120, max(24, int(np.ceil((max_lon - min_lon) / deg_res))))
        height = min(120, max(24, int(np.ceil((max_lat - min_lat) / deg_res))))

        np.random.seed(43)
        # Realistic Sentinel-1 VV backscatter for crops: mean ~ -12.4 dB (range -19 to -6 dB)
        vv = np.random.normal(-12.4, 2.2, size=(height, width)).astype(np.float32)
        vv = np.clip(vv, -19.22, -6.31)

        # Realistic Sentinel-1 VH backscatter for crops: mean ~ -18.7 dB (range -25 to -11 dB)
        vh = np.random.normal(-18.7, 2.1, size=(height, width)).astype(np.float32)
        vh = np.clip(vh, -25.14, -11.08)

        sim_date = end_date if end_date else "2026-09-14"
        sim_timestamp = f"{sim_date}T00:00:00Z"

        return {
            "available": True,
            "timestamp": sim_timestamp,
            "orbit_direction": "DESCENDING",
            "polarization": ["VV", "VH"],
            "vv": vv,
            "vh": vh,
            "data_quality": "GOOD",
            "is_simulated": True
        }

