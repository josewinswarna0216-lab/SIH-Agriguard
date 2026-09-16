"""NDVI calculation and vegetation statistical analysis.

Provides vectorized NumPy calculations for Normalized Difference Vegetation Index (NDVI),
safe handling of division by zero, invalid data masking, and summary metrics.
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


def calculate_ndvi_from_bands(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Calculate NDVI from Sentinel-2 Red (B04) and Near-Infrared (B08) reflectance bands.

    Formula:
        NDVI = (NIR - Red) / (NIR + Red)

    Handles division by zero and clamps output to [-1.0, 1.0].

    Args:
        red: 2D numpy array of B04 reflectance.
        nir: 2D numpy array of B08 reflectance.

    Returns:
        np.ndarray: 2D float32 array with NDVI values [-1.0, 1.0].
    """
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)

    denom = nir + red
    # Use small epsilon to avoid divide-by-zero warnings
    valid_denom = denom > 1e-5

    ndvi = np.zeros_like(red, dtype=np.float32)
    np.divide(nir - red, denom, out=ndvi, where=valid_denom)

    # Clamp physically possible NDVI bounds [-1.0, 1.0]
    np.clip(ndvi, -1.0, 1.0, out=ndvi)
    return ndvi


def compute_vegetation_statistics(
    ndvi: np.ndarray,
    valid_mask: np.ndarray
) -> Dict[str, float]:
    """Compute summary statistics for valid vegetation pixels.

    Args:
        ndvi: 2D float array of NDVI values.
        valid_mask: 2D boolean array (True = valid, non-cloud farm pixel).

    Returns:
        dict containing:
            - mean_ndvi: float
            - minimum_ndvi: float
            - maximum_ndvi: float
            - valid_pixel_percentage: float (0 - 100)
    """
    total_pixels = valid_mask.size
    valid_pixel_count = int(np.sum(valid_mask))

    if total_pixels == 0 or valid_pixel_count == 0:
        logger.warning("No valid pixels found for vegetation statistical calculation.")
        return {
            "mean_ndvi": 0.0,
            "minimum_ndvi": 0.0,
            "maximum_ndvi": 0.0,
            "valid_pixel_percentage": 0.0
        }

    valid_values = ndvi[valid_mask]

    mean_val = float(np.mean(valid_values))
    min_val = float(np.min(valid_values))
    max_val = float(np.max(valid_values))
    valid_pct = (valid_pixel_count / total_pixels) * 100.0

    return {
        "mean_ndvi": round(mean_val, 2),
        "minimum_ndvi": round(min_val, 2),
        "maximum_ndvi": round(max_val, 2),
        "valid_pixel_percentage": round(valid_pct, 1)
    }


def calculate_ndwi_from_bands(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """Calculate NDWI (Normalized Difference Water Index - Gao 1996) from NIR (B08) and SWIR1 (B11).

    Formula:
        NDWI = (NIR - SWIR) / (NIR + SWIR)

    Measures vegetation liquid water content. Handles division by zero safely and clamps output to [-1.0, 1.0].

    Args:
        nir: 2D numpy array of B08 NIR reflectance.
        swir: 2D numpy array of B11 SWIR1 reflectance.

    Returns:
        np.ndarray: 2D float32 array with NDWI values [-1.0, 1.0].
    """
    nir = nir.astype(np.float32)
    swir = swir.astype(np.float32)

    denom = nir + swir
    valid_denom = denom > 1e-5

    ndwi = np.zeros_like(nir, dtype=np.float32)
    np.divide(nir - swir, denom, out=ndwi, where=valid_denom)
    np.clip(ndwi, -1.0, 1.0, out=ndwi)
    return ndwi


def compute_index_stats_4(
    data_array: np.ndarray,
    valid_mask: Optional[np.ndarray] = None
) -> Dict[str, Optional[float]]:
    """Compute 4-metric statistics (mean, min, max, std) over valid non-cloud/non-NaN pixels.

    Args:
        data_array: 2D float array of index values.
        valid_mask: Optional 2D boolean mask.

    Returns:
        dict containing mean, min, max, std (or Nones if no valid pixels exist).
    """
    if data_array is None or data_array.size == 0:
        return {"mean": None, "min": None, "max": None, "std": None}

    mask = valid_mask if valid_mask is not None else np.ones_like(data_array, dtype=bool)
    combined_mask = mask & ~np.isnan(data_array) & ~np.isinf(data_array) & (data_array != -999.0)

    if not np.any(combined_mask):
        return {"mean": None, "min": None, "max": None, "std": None}

    valid_vals = data_array[combined_mask]
    return {
        "mean": round(float(np.mean(valid_vals)), 2),
        "min": round(float(np.min(valid_vals)), 2),
        "max": round(float(np.max(valid_vals)), 2),
        "std": round(float(np.std(valid_vals)), 2)
    }


def compute_radar_stats_3(
    data_array: np.ndarray,
    valid_mask: Optional[np.ndarray] = None
) -> Dict[str, Optional[float]]:
    """Compute 3-metric radar statistics (mean, min, max) over valid non-NaN backscatter pixels.

    Args:
        data_array: 2D float array of SAR backscatter values (dB).
        valid_mask: Optional 2D boolean mask.

    Returns:
        dict containing mean, min, max (or Nones if no valid pixels exist).
    """
    if data_array is None or data_array.size == 0:
        return {"mean": None, "min": None, "max": None}

    mask = valid_mask if valid_mask is not None else np.ones_like(data_array, dtype=bool)
    combined_mask = mask & ~np.isnan(data_array) & ~np.isinf(data_array) & (data_array != -999.0)

    if not np.any(combined_mask):
        return {"mean": None, "min": None, "max": None}

    valid_vals = data_array[combined_mask]
    return {
        "mean": round(float(np.mean(valid_vals)), 2),
        "min": round(float(np.min(valid_vals)), 2),
        "max": round(float(np.max(valid_vals)), 2)
    }

