"""Cloud filtering and pixel validity masking for Sentinel-2 L2A data.

Uses Sentinel-2 L2A Scene Classification Layer (SCL) and dataMask to filter out:
- Cloud shadows
- High and medium probability clouds
- Thin cirrus clouds
- Saturated or defective sensor pixels
- Snow / ice
- No-data pixels
- Pixels outside the farm polygon boundary
"""

import logging
from typing import Tuple, Set, Optional
import numpy as np
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)

# Standard Sentinel-2 L2A Scene Classification Layer (SCL) classes:
# 0: NO_DATA
# 1: SATURATED_OR_DEFECTIVE
# 2: DARK_AREA_PIXELS
# 3: CLOUD_SHADOWS
# 4: VEGETATION
# 5: NOT_VEGETATED
# 6: WATER
# 7: UNCLASSIFIED
# 8: CLOUD_MEDIUM_PROBABILITY
# 9: CLOUD_HIGH_PROBABILITY
# 10: THIN_CIRRUS
# 11: SNOW_OR_ICE

# SCL classes deemed invalid for vegetation analysis
INVALID_SCL_CLASSES: Set[int] = {
    0,   # NO_DATA
    1,   # SATURATED_OR_DEFECTIVE
    3,   # CLOUD_SHADOWS
    8,   # CLOUD_MEDIUM_PROBABILITY
    9,   # CLOUD_HIGH_PROBABILITY
    10,  # THIN_CIRRUS
    11,  # SNOW
}


def apply_scl_cloud_mask(
    scl_array: np.ndarray,
    datamask_array: np.ndarray,
    farm_mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """Generate a boolean mask where True indicates valid, cloud-free farm pixels.

    Methodology:
    1. Satellite Footprint: Must have dataMask == 1 (inside satellite swath).
    2. Atmospheric & Quality Filtering: SCL must NOT belong to clouds (classes 8, 9, 10),
       cloud shadows (class 3), saturated/defective pixels (class 1), or snow (class 11).
    3. Boundary Alignment: If a farm polygon mask is provided, pixels outside
       the polygon boundary are excluded.

    Args:
        scl_array: 2D integer or float array containing SCL classification values.
        datamask_array: 2D array where 1 = valid tile data, 0 = no-data.
        farm_mask: Optional 2D boolean array where True = inside farm boundary.

    Returns:
        np.ndarray: 2D boolean array where True = clean, usable vegetation pixel.
    """
    scl_rounded = np.round(scl_array).astype(int)

    # 1. Start with dataMask (1 = valid satellite data)
    valid = (datamask_array > 0.5)

    # 2. Exclude cloudy, shadow, and corrupted pixels
    for invalid_class in INVALID_SCL_CLASSES:
        valid = valid & (scl_rounded != invalid_class)

    # 3. Apply farm boundary polygon mask if provided
    if farm_mask is not None:
        valid = valid & farm_mask

    logger.debug(
        f"Cloud mask generated: {np.sum(valid)} valid pixels out of {valid.size} "
        f"({(np.sum(valid) / valid.size) * 100:.1f}%)"
    )

    return valid


def calculate_cloud_fraction(
    scl_array: np.ndarray,
    datamask_array: np.ndarray,
    farm_mask: Optional[np.ndarray] = None
) -> float:
    """Calculate the cloud and shadow percentage over the area of interest.

    Args:
        scl_array: 2D SCL array.
        datamask_array: 2D dataMask array.
        farm_mask: Optional 2D farm polygon mask.

    Returns:
        float: Cloud + shadow percentage (0.0 - 100.0).
    """
    scl_rounded = np.round(scl_array).astype(int)
    scope = (datamask_array > 0.5)
    if farm_mask is not None:
        scope = scope & farm_mask

    total_farm_pixels = np.sum(scope)
    if total_farm_pixels == 0:
        return 100.0

    cloud_shadow_pixels = (
        (scl_rounded == 3) |  # Shadow
        (scl_rounded == 8) |  # Medium cloud
        (scl_rounded == 9) |  # High cloud
        (scl_rounded == 10)   # Cirrus
    ) & scope

    cloud_fraction = (np.sum(cloud_shadow_pixels) / total_farm_pixels) * 100.0
    return float(np.round(cloud_fraction, 2))
