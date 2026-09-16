# Integration Contract: Satellite / Geospatial Module ↔ Risk Engine

**Module Responsible:** Person 2 (Satellite & Geospatial Integration)  
**Consumer:** Person 1 (Weather & Crop Disease Risk Engine)  
**Service Version:** `1.0.0`  
**Endpoint:** `POST /api/satellite/analyze`  
**Base URL (Local):** `http://127.0.0.1:8000`

---

## 1. Overview & Semantic Responsibility

The Satellite Module processes Sentinel-2 L2A optical satellite imagery over a farmer's field boundary, performs cloud and shadow filtering, calculates NDVI (Normalized Difference Vegetation Index), detects vegetative stress, and outputs georeferenced affected zones.

> [!IMPORTANT]
> **Semantic Responsibility Notice:**  
> The satellite module detects **"Potential vegetation stress"** and spectral reflectance anomalies. It does **NOT** confirm biological plant disease. Person 1's Risk Engine combines this vegetation stress indicator with weather variables (temperature, relative humidity, leaf wetness, rainfall) and crop phenology to compute the true disease probability.

---

## 2. Request Specification

### HTTP Request
- **Method:** `POST`
- **Path:** `/api/satellite/analyze`
- **Headers:** `Content-Type: application/json`

### JSON Request Schema

```json
{
  "field_id": "FIELD_001",
  "crop": "potato",
  "polygon": {
    "type": "Polygon",
    "coordinates": [
      [
        [80.123, 13.012],
        [80.128, 13.012],
        [80.128, 13.018],
        [80.123, 13.018],
        [80.123, 13.012]
      ]
    ]
  },
  "bbox": [80.123, 13.012, 80.128, 13.018],
  "start_date": "2026-08-15",
  "end_date": "2026-09-14",
  "baseline_start_date": "2025-08-15",
  "baseline_end_date": "2025-09-14",
  "max_cloud_cover": 20.0
}
```

### Request Fields

| Field | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `field_id` | `string` | **Yes** | — | Unique identifier of the agricultural field (e.g. `FIELD_001`). |
| `crop` | `string` | No | `"unknown"` | Crop name (e.g. `potato`, `tomato`, `wheat`, `rice`). |
| `polygon` | `GeoJSON Polygon` | **Yes\*** | `null` | Boundary coordinates in WGS84 `[longitude, latitude]` order (RFC 7946). Outer ring must be closed. |
| `bbox` | `array[float]` | **Yes\*** | `null` | Alternative bounding box `[min_lon, min_lat, max_lon, max_lat]` for quick testing. |
| `start_date` | `string` | **Yes** | — | Beginning of imagery search window (`YYYY-MM-DD`). |
| `end_date` | `string` | **Yes** | — | End of imagery search window (`YYYY-MM-DD`). |
| `baseline_start_date`| `string` | No | `null` | Optional historical search start date (`YYYY-MM-DD`) for anomaly delta. |
| `baseline_end_date` | `string` | No | `null` | Optional historical search end date (`YYYY-MM-DD`) for anomaly delta. |
| `max_cloud_cover` | `float` | No | `20.0` | Maximum acceptable scene-level cloud cover percentage ($0.0 - 100.0$). |

*\* Either `polygon` or `bbox` must be provided.*

---

## 3. Response Specification

### HTTP Response (Status 200 OK)

```json
{
  "field_id": "FIELD_001",
  "crop": "potato",
  "analysis_timestamp": "2026-09-15T14:30:00Z",
  "is_simulated": false,
  "satellite": {
    "source": "Sentinel-2",
    "processing_level": "L2A",
    "image_date": "2026-09-13",
    "cloud_percentage": 4.8
  },
  "vegetation": {
    "mean_ndvi": 0.63,
    "minimum_ndvi": 0.31,
    "maximum_ndvi": 0.86,
    "valid_pixel_percentage": 95.2
  },
  "stress": {
    "level": "MODERATE",
    "classification_label": "Potential vegetation stress",
    "total_area_hectares": 35.8,
    "stressed_area_hectares": 4.9,
    "stressed_area_percentage": 13.7,
    "baseline_mean_ndvi": 0.75,
    "ndvi_change": -0.12,
    "ndvi_change_percentage": -16.0
  },
  "affected_zone": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "stress_level": "HIGH",
          "mean_ndvi": 0.38,
          "area_hectares": 4.9
        },
        "geometry": {
          "type": "Polygon",
          "coordinates": [
            [
              [80.1251, 13.0132],
              [80.1278, 13.0132],
              [80.1278, 13.0155],
              [80.1251, 13.0155],
              [80.1251, 13.0132]
            ]
          ]
        }
      }
    ]
  },
  "outputs": {
    "ndvi_map": "/outputs/FIELD_001_ndvi.png",
    "stress_map": "/outputs/FIELD_001_stress.png",
    "affected_geojson": "/outputs/FIELD_001_affected.geojson"
  }
}
```

### Response Field Descriptions

#### 1. `satellite` (Acquisition Metadata)
- `source`: Satellite constellation (`Sentinel-2`).
- `processing_level`: Bottom-of-Atmosphere surface reflectance (`L2A`).
- `image_date`: Exact date when the satellite captured the image (`YYYY-MM-DD`).
- `cloud_percentage`: Cloud coverage percentage over the scene.

#### 2. `vegetation` (Canopy Indices)
- `mean_ndvi`: Average canopy NDVI over all valid vegetation pixels.
- `minimum_ndvi`: Minimum NDVI detected inside the field.
- `maximum_ndvi`: Maximum peak vegetation NDVI.
- `valid_pixel_percentage`: Percentage of field pixels that were usable after masking clouds, shadows, and water.

#### 3. `stress` (Vegetation Anomaly & Severity)
- `level`: Categorical stress rating: `HEALTHY`, `MODERATE`, or `HIGH`.
- `classification_label`: Fixed standard label `"Potential vegetation stress"`.
- `total_area_hectares`: Total farm area calculated using WGS84 geodesic ellipsoidal geometry.
- `stressed_area_hectares`: Absolute surface area experiencing high vegetation stress.
- `stressed_area_percentage`: Percentage of farm area afflicted by high stress.
- `baseline_mean_ndvi`: Historical baseline mean NDVI (if baseline requested).
- `ndvi_change`: $\Delta \text{NDVI} = \text{Current NDVI} - \text{Baseline NDVI}$.
- `ndvi_change_percentage`: Percentage change relative to baseline.

#### 4. `affected_zone` (GeoJSON Vector Features)
- Standard RFC 7946 GeoJSON `FeatureCollection`.
- Polygons are **strictly clipped** to the farm boundary.
- Isolated noise pixels smaller than `MIN_STRESS_AREA_HECTARES` are filtered out.
- Each feature contains:
  - `stress_level`: `"HIGH"`
  - `mean_ndvi`: Average NDVI within this anomaly polygon
  - `area_hectares`: Exact area in hectares of this affected patch

#### 5. `outputs` (Visualization Artifacts)
- `ndvi_map`: URL path to the generated NDVI PNG map (`/outputs/{field_id}_ndvi.png`).
- `stress_map`: URL path to the 3-tier classification PNG map (`/outputs/{field_id}_stress.png`).
- `affected_geojson`: URL path to the stored GeoJSON (`/outputs/{field_id}_affected.geojson`).

---

## 4. HTTP Error Status Codes

| Status Code | Description | Cause |
| :--- | :--- | :--- |
| `400 Bad Request` | Invalid Input | Coordinates out of bounds, invalid GeoJSON, start date after end date, farm area < 0.01 ha, or all scenes too cloudy. |
| `401 Unauthorized` | Auth Error | Sentinel Hub credentials missing or invalid when `DEMO_MODE=false`. |
| `404 Not Found` | No Image / No Result | No satellite imagery found within date window, or field_id not found in `/result/{field_id}`. |
| `500 Internal Error`| Server Error | Unexpected processing failure (check server logs). |

---

## 5. Person 1 Python Integration Example

Person 1 can consume this API with standard `requests`:

```python
import requests

SATELLITE_SERVICE_URL = "http://127.0.0.1:8000/api/satellite/analyze"

payload = {
    "field_id": "FIELD_001",
    "crop": "potato",
    "polygon": {
        "type": "Polygon",
        "coordinates": [
            [
                [80.123, 13.012],
                [80.128, 13.012],
                [80.128, 13.018],
                [80.123, 13.018],
                [80.123, 13.012]
            ]
        ]
    },
    "start_date": "2026-08-15",
    "end_date": "2026-09-14"
}

response = requests.post(SATELLITE_SERVICE_URL, json=payload, timeout=30)
response.raise_for_status()
satellite_data = response.json()

# Extract variables for Disease Risk Engine
stress_level = satellite_data["stress"]["level"]
stressed_pct = satellite_data["stress"]["stressed_area_percentage"]
mean_ndvi = satellite_data["vegetation"]["mean_ndvi"]
affected_zones = satellite_data["affected_zone"]["features"]

print(f"Field Stress: {stress_level}, Affected: {stressed_pct}%, Mean NDVI: {mean_ndvi}")
print(f"Identified {len(affected_zones)} high-stress polygon zones for field inspection.")
```
