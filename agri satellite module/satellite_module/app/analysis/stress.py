"""Vegetation stress classification and map visualization.

Applies configurable thresholds to detect vegetation stress / anomalies (NOT confirmed disease),
calculates high-stress pixel masks, and generates NDVI and stress map PNG visualizations.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend for server environments
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches

from ..config import settings, OUTPUTS_DIR

logger = logging.getLogger(__name__)


def classify_vegetation_stress(
    ndvi: np.ndarray,
    valid_mask: np.ndarray,
    healthy_threshold: Optional[float] = None,
    moderate_threshold: Optional[float] = None
) -> Tuple[np.ndarray, str, np.ndarray]:
    """Classify pixels into HEALTHY, MODERATE STRESS, or HIGH STRESS categories.

    IMPORTANT:
    This detects potential vegetation stress and anomalies from spectral reflectance.
    It does NOT claim to confirm plant disease (ground truth / scouting is required).

    Thresholds:
        NDVI >= healthy_threshold: HEALTHY (Value = 1)
        moderate_threshold <= NDVI < healthy_threshold: MODERATE STRESS (Value = 2)
        NDVI < moderate_threshold: HIGH STRESS (Value = 3)
        Invalid / cloud / outside farm: MASKED (Value = 0)

    Args:
        ndvi: 2D array of NDVI values.
        valid_mask: 2D boolean array of valid farm pixels.
        healthy_threshold: Configurable upper threshold (default: 0.65).
        moderate_threshold: Configurable lower threshold (default: 0.45).

    Returns:
        Tuple containing:
            - stress_grid: 2D integer array (0: Masked, 1: Healthy, 2: Moderate, 3: High)
            - overall_level: "HEALTHY", "MODERATE", or "HIGH"
            - high_stress_mask: 2D boolean array (True where stress is HIGH)
    """
    h_thresh = healthy_threshold if healthy_threshold is not None else settings.NDVI_HEALTHY_THRESHOLD
    m_thresh = moderate_threshold if moderate_threshold is not None else settings.NDVI_MODERATE_THRESHOLD

    stress_grid = np.zeros_like(ndvi, dtype=np.uint8)

    # Apply classifications only to valid pixels
    healthy_cond = valid_mask & (ndvi >= h_thresh)
    moderate_cond = valid_mask & (ndvi >= m_thresh) & (ndvi < h_thresh)
    high_cond = valid_mask & (ndvi < m_thresh)

    stress_grid[healthy_cond] = 1   # Healthy
    stress_grid[moderate_cond] = 2  # Moderate stress
    stress_grid[high_cond] = 3      # High stress

    total_valid = np.sum(valid_mask)
    if total_valid == 0:
        return stress_grid, "HEALTHY", high_cond

    high_count = np.sum(high_cond)
    moderate_count = np.sum(moderate_cond)

    high_pct = (high_count / total_valid) * 100.0
    moderate_pct = (moderate_count / total_valid) * 100.0

    # Determine field-level overall severity
    if high_pct >= 10.0 or (high_pct + moderate_pct) >= 40.0:
        overall_level = "HIGH"
    elif high_pct >= 3.0 or moderate_pct >= 15.0:
        overall_level = "MODERATE"
    else:
        overall_level = "HEALTHY"

    logger.debug(
        f"Stress classification: Healthy={np.sum(healthy_cond)}, "
        f"Moderate={moderate_count} ({moderate_pct:.1f}%), "
        f"High={high_count} ({high_pct:.1f}%). Overall: {overall_level}"
    )

    return stress_grid, overall_level, high_cond


def generate_ndvi_and_stress_maps(
    field_id: str,
    ndvi: np.ndarray,
    valid_mask: np.ndarray,
    stress_grid: np.ndarray,
    output_dir: Optional[Path] = None
) -> Tuple[str, str]:
    """Generate and save NDVI and vegetation stress visualization PNG maps.

    Args:
        field_id: Field identifier for filename.
        ndvi: 2D float array of NDVI.
        valid_mask: 2D boolean mask.
        stress_grid: 2D int array (0: Masked, 1: Healthy, 2: Moderate, 3: High).
        output_dir: Directory where PNG maps will be stored.

    Returns:
        Tuple[str, str]: (ndvi_map_path, stress_map_path)
    """
    out_dir = output_dir or settings.OUTPUT_PATH
    out_dir.mkdir(parents=True, exist_ok=True)

    ndvi_filename = f"{field_id}_ndvi.png"
    stress_filename = f"{field_id}_stress.png"
    ndvi_path = out_dir / ndvi_filename
    stress_path = out_dir / stress_filename

    # -------------------------------------------------------------
    # 1. NDVI Map (Red -> Yellow -> Green)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    # Mask invalid pixels
    masked_ndvi = np.ma.masked_where(~valid_mask, ndvi)

    cmap = matplotlib.colormaps["RdYlGn"]
    cmap.set_bad(color="lightgray", alpha=0.3)

    im = ax.imshow(masked_ndvi, cmap=cmap, vmin=-0.1, vmax=0.9, origin="upper")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("NDVI Value", fontsize=9)

    ax.set_title(f"NDVI Map — Field {field_id}", fontsize=11, fontweight="bold", pad=8)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(ndvi_path, bbox_inches="tight", dpi=150)
    plt.close(fig)

    # -------------------------------------------------------------
    # 2. Stress Map (Green: Healthy, Yellow: Moderate, Red: High)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)

    # Custom colormap for classes:
    # 0: Background/Cloud (Transparent/Light Gray)
    # 1: Healthy (Green)
    # 2: Moderate Stress (Yellow/Orange)
    # 3: High Stress (Red)
    stress_colors = ["#E0E0E0", "#2ECC71", "#F39C12", "#E74C3C"]
    stress_cmap = ListedColormap(stress_colors)
    bounds = [-0.5, 0.5, 1.5, 2.5, 3.5]
    norm = BoundaryNorm(bounds, stress_cmap.N)

    ax.imshow(stress_grid, cmap=stress_cmap, norm=norm, origin="upper")
    ax.set_title(f"Vegetation Stress Map — Field {field_id}", fontsize=11, fontweight="bold", pad=8)
    ax.axis("off")

    # Legend
    legend_patches = [
        mpatches.Patch(color="#2ECC71", label="Healthy (NDVI ≥ 0.65)"),
        mpatches.Patch(color="#F39C12", label="Moderate Stress (0.45 ≤ NDVI < 0.65)"),
        mpatches.Patch(color="#E74C3C", label="High Stress / Anomaly (NDVI < 0.45)"),
        mpatches.Patch(color="#E0E0E0", label="Masked / Cloud / Non-farm")
    ]
    ax.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.22),
              ncol=2, fontsize=7.5, frameon=True)

    plt.tight_layout()
    plt.savefig(stress_path, bbox_inches="tight", dpi=150)
    plt.close(fig)

    logger.info(f"Saved maps: {ndvi_path.name} and {stress_path.name}")
    return str(ndvi_path), str(stress_path)
