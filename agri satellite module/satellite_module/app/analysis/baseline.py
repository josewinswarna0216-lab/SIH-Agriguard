"""Historical baseline comparison for NDVI anomaly detection.

Compares current field NDVI against historical multi-temporal baseline imagery
to detect sudden vegetation deterioration or seasonal anomalies.
"""

import logging
from typing import Dict, Any, Optional
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)


def compare_with_historical_baseline(
    current_mean_ndvi: float,
    baseline_mean_ndvi: Optional[float] = None
) -> Dict[str, Optional[float]]:
    """Compute vegetation change relative to historical baseline.

    Args:
        current_mean_ndvi: Mean NDVI of the current acquisition.
        baseline_mean_ndvi: Mean NDVI from historical baseline period (if available).

    Returns:
        dict containing:
            - baseline_mean_ndvi: float or None
            - ndvi_change: float (current - baseline) or None
            - ndvi_change_percentage: float or None
    """
    if baseline_mean_ndvi is None or baseline_mean_ndvi <= 0.0:
        logger.info("No valid historical baseline provided; proceeding with current status only.")
        return {
            "baseline_mean_ndvi": None,
            "ndvi_change": None,
            "ndvi_change_percentage": None
        }

    ndvi_change = current_mean_ndvi - baseline_mean_ndvi
    pct_change = (ndvi_change / baseline_mean_ndvi) * 100.0

    logger.info(
        f"Baseline comparison: Current={current_mean_ndvi:.2f}, "
        f"Baseline={baseline_mean_ndvi:.2f}, "
        f"Change={ndvi_change:+.2f} ({pct_change:+.1f}%)"
    )

    return {
        "baseline_mean_ndvi": round(baseline_mean_ndvi, 2),
        "ndvi_change": round(ndvi_change, 2),
        "ndvi_change_percentage": round(pct_change, 1)
    }
