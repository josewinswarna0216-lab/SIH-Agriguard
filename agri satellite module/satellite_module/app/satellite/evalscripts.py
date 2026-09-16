"""Sentinel Hub Evalscripts for Sentinel-2 L2A Imagery.

Provides Version 3 evalscripts for computing NDVI, extracting SCL (Scene Classification Layer),
and validating data masks.
"""

S2_L2A_NDVI_SCL_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [
      {
        bands: ["B04", "B08", "SCL", "dataMask"],
        units: "REFLECTANCE"
      }
    ],
    output: {
      bands: 5,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(sample) {
  // B04 = Red (approx 665 nm, 10m resolution)
  // B08 = Near Infrared (approx 842 nm, 10m resolution)
  // SCL = Scene Classification Layer (20m resolution)
  // dataMask = 1 for valid satellite footprint, 0 for outside tile
  
  let red = sample.B04;
  let nir = sample.B08;
  let denom = nir + red;
  let ndvi = -999.0; // Default no-data flag
  
  // Safe NDVI calculation: prevent division by zero or negative denominators
  if (denom > 0.00001) {
    let raw_ndvi = (nir - red) / denom;
    // Clamp NDVI between -1.0 and +1.0
    ndvi = Math.max(-1.0, Math.min(1.0, raw_ndvi));
  }
  
  // Return [NDVI, SCL, dataMask, B04, B08]
  return [ndvi, sample.SCL, sample.dataMask, red, nir];
}
"""

# Enhanced Evalscript for Sentinel-2 L2A fetching Red (B04), NIR (B08), SWIR1 (B11), Green (B03), SCL, and dataMask
S2_L2A_NDVI_NDWI_SCL_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [
      {
        bands: ["B03", "B04", "B08", "B11", "SCL", "dataMask"],
        units: "REFLECTANCE"
      }
    ],
    output: {
      bands: 7,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(sample) {
  let red = sample.B04;
  let nir = sample.B08;
  let swir = sample.B11;
  let green = sample.B03;
  
  let ndvi = -999.0;
  let denom_ndvi = nir + red;
  if (denom_ndvi > 0.00001) {
    ndvi = Math.max(-1.0, Math.min(1.0, (nir - red) / denom_ndvi));
  }
  
  // NDWI (Gao 1996 Vegetation Water Content): (NIR - SWIR) / (NIR + SWIR)
  let ndwi = -999.0;
  let denom_ndwi = nir + swir;
  if (denom_ndwi > 0.00001) {
    ndwi = Math.max(-1.0, Math.min(1.0, (nir - swir) / denom_ndwi));
  }
  
  // Return [NDVI, NDWI, SCL, dataMask, B04 (Red), B08 (NIR), B11 (SWIR1)]
  return [ndvi, ndwi, sample.SCL, sample.dataMask, red, nir, swir];
}
"""

# Sentinel-1 Synthetic Aperture Radar (IW GRD) Evalscript for VV and VH polarizations
S1_IW_GRD_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [
      {
        bands: ["VV", "VH", "dataMask"]
      }
    ],
    output: {
      bands: 3,
      sampleType: "FLOAT32"
    }
  };
}

function evaluatePixel(sample) {
  // Return [VV, VH, dataMask] in decibels (dB) / linear reflectance
  return [sample.VV, sample.VH, sample.dataMask];
}
"""

# Simple RGB True Color Evalscript for visual verification if needed
S2_L2A_TRUE_COLOR_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "dataMask"],
    output: { bands: 4, sampleType: "AUTO" }
  };
}
function evaluatePixel(sample) {
  return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02, sample.dataMask];
}
"""

