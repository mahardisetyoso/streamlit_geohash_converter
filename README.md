<p align="center">
  <h1 align="center">🗺️ Geohash Converter</h1>
  <p align="center">
    <strong>Draw. Convert. Download. Geospatial ops in seconds, not hours.</strong>
  </p>
  <p align="center">
    <a href="https://geohashconverter.streamlit.app/"><img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Open in Streamlit"></a>
  </p>
  <p align="center">
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python"></a>
    <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/Streamlit-1.37-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit"></a>
    <a href="https://python-visualization.github.io/folium/"><img src="https://img.shields.io/badge/Folium-0.17-77B829?logo=leaflet&logoColor=white" alt="Folium"></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  </p>
</p>

---

## The Problem

You're a mapping ops engineer. Your team needs geohash coverage for a new service zone — **yesterday**.

The old workflow: export polygon from QGIS → write a Python script → run locally → manually validate on map → format output → send CSV to stakeholders. **45 minutes. Every. Single. Time.**

This tool does it in **under 30 seconds**: draw a polygon on an interactive map, pick your precision, hit download.

---

## Demo

> 🔴 **[Try it live →](https://geohashconverter.streamlit.app/)** — no installation needed.

### ✏️ Draw a Polygon → Get Geohashes Instantly

> Draw any shape on the map. The tool converts your polygon into geohash cells at your chosen precision (1–12), overlays them in real-time, and lets you download the results in multiple formats.

<p align="center">
  <img src="assets/demo_draw.gif" alt="Draw polygon and get geohashes" width="720">
</p>

### 📋 Paste Coordinates → Visualize on Map

> Already have a coordinate list? Paste it, choose precision, and see geohash cells rendered on a Folium map — no code required.

<p align="center">
  <img src="assets/demo_paste.gif" alt="Paste coordinates and convert" width="720">
</p>

---

## Features

### 🎯 Five Conversion Modes

| Mode | Input | Output | Use Case |
|------|-------|--------|----------|
| **Draw Polygon** | Freehand polygon on map | Geohash list + overlay | Define new service zones, geofencing |
| **Copy Coordinates** | Comma-separated lat/lng | Geohash list + map viz | Convert existing coordinate data |
| **Bulk Extraction** | GeoJSON file upload | Geohash coverage for entire area | City-wide / regional coverage maps |
| **Geohash Visualizer** | Paste geohash strings | Interactive map with cells | QA / validate existing geohash sets |
| **GeoJSON → CSV** | GeoJSON polygon file | CSV with extracted coordinates | Data pipeline preprocessing |

### 🎨 Visualization Controls

- **Precision slider** (1–12): from continent-scale to doorstep-level
- **Inner coverage mode**: strict containment within polygon boundary
- **Color-coded cells**: automatic coloring by precision level
- **Opacity & weight controls**: fine-tune map rendering
- **Centroid markers**: optional clustered markers for cell centers
- **Cell count limiter**: keep the map responsive on large areas

### 📦 Export Formats

| Format | Description |
|--------|-------------|
| `CSV` | One geohash per row — ready for database import |
| `TXT (comma)` | Comma-separated string — paste directly into queries |
| `TXT (newline)` | One per line — grep/awk friendly |
| `JSON array` | `["qqgux", "qqguy", ...]` — API-ready |
| `GeoJSON polygons` | Full cell geometries — load into QGIS, Kepler.gl, or any GIS tool |
| `ZIP (compressed)` | GeoJSON wrapped in ZIP — smaller transfer size |

---

## Quick Start

### Run Locally

```bash
# Clone
git clone https://github.com/mahardisetyoso/streamlit_geohash_converter.git
cd streamlit_geohash_converter

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run Home.py
```

Open `http://localhost:8501` → start drawing.

### Requirements

```
Python 3.12
folium==0.17.0
geopandas==0.13.0
shapely==2.0.1
streamlit==1.37.0
streamlit-folium==0.21.0
polygeohasher
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│  USER INPUT                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Draw on  │  │  Paste   │  │  Upload  │              │
│  │   Map     │  │  Coords  │  │  GeoJSON │              │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
│        │              │              │                    │
│        ▼              ▼              ▼                    │
│  ┌─────────────────────────────────────────┐             │
│  │  Shapely Polygon (EPSG:4326)            │             │
│  └─────────────────┬───────────────────────┘             │
│                    │                                      │
│                    ▼                                      │
│  ┌─────────────────────────────────────────┐             │
│  │  polygeohasher.create_geohash_list()    │             │
│  │  ├── Precision: 1-12 (user-selected)    │             │
│  │  └── Mode: inner / full coverage        │             │
│  └─────────────────┬───────────────────────┘             │
│                    │                                      │
│                    ▼                                      │
│  ┌─────────────────────────────────────────┐             │
│  │  OUTPUT                                 │             │
│  │  ├── Folium map overlay (interactive)   │             │
│  │  ├── Geohash list (CSV/JSON/TXT/GeoJSON)│             │
│  │  └── Stats: count, precision, coverage  │             │
│  └─────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## Use Cases

### 🚗 Fleet & Ride-Hailing Operations
Define service zones, coverage areas, and geofence boundaries for driver dispatch systems. Convert operational polygons into geohash grids for backend matching engines.

### 📍 Geofencing & Location Services
Generate geohash coverage for notification triggers, marketing zones, or restricted areas. Export directly to database-ready formats.

### 🗺️ Mapping & GIS Workflows
QA tool for validating geohash assignments. Visualize coverage gaps. Convert between coordinate formats without writing scripts.

### 📊 Data Engineering Pipelines
Preprocessing step: convert GeoJSON boundaries into geohash lists for spatial joins, partitioning keys, or indexing in data warehouses (BigQuery, DuckDB, PostgreSQL).

---

## Geohash Precision Reference

| Precision | Cell Size (approx.) | Example Use |
|-----------|---------------------|-------------|
| 1 | ~5,000 km | Continent |
| 2 | ~1,250 km | Country |
| 3 | ~156 km | State / Region |
| 4 | ~39 km | City |
| 5 | ~5 km | District / Neighborhood |
| **6** | **~1.2 km** | **Block (default)** |
| 7 | ~153 m | Street segment |
| 8 | ~38 m | Building |
| 9 | ~5 m | Parking spot |
| 10–12 | < 1 m | Centimeter-level |

---

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **Frontend** | Streamlit | Rapid Python-native web apps, zero JS needed |
| **Maps** | Folium + Leaflet.draw | Interactive maps with freehand drawing support |
| **Geospatial** | GeoPandas + Shapely | Industry-standard geometry operations |
| **Geohash Engine** | polygeohasher | Polygon-to-geohash conversion with inner/outer modes |
| **Custom Plugin** | NewDraw (Leaflet extension) | Extended drawing controls with persistent FeatureGroup |

---

## Project Structure

```
streamlit_geohash_converter/
├── Home.py                              # Landing page with video demos
├── newdraw.py                           # Custom Leaflet.draw extension
├── requirements.txt                     # Python dependencies
├── runtime.txt                          # Python 3.12
├── .streamlit/config.toml               # Theme configuration
└── pages/
    ├── Copy_Coordinates.py              # Paste coords → geohash
    ├── Drawing_Polygon.py               # Draw polygon → geohash (main feature)
    ├── Bulk_Extraction.py               # Upload GeoJSON → bulk geohash
    ├── GeoJSON_to_csv_Coordinates.py    # GeoJSON → CSV converter
    ├── Geohash_Visualization_by_Copying.py  # Visualize geohash list on map
    ├── Personal_Information.py          # About the author
    ├── jakarta.geojson                  # Sample data (Jakarta boundary)
    ├── pic1.mp4                         # Demo: coordinate conversion
    └── pic2.mp4                         # Demo: polygon drawing
```

---

## Roadmap

- [x] Polygon drawing → geohash conversion
- [x] Coordinate paste → geohash conversion
- [x] Bulk GeoJSON upload
- [x] Multi-format export (CSV, JSON, TXT, GeoJSON, ZIP)
- [x] Precision-based color coding
- [x] Inner/outer coverage mode
- [ ] H3 hexagonal indexing support (Uber's spatial system)
- [ ] Batch processing: multiple polygons in single upload
- [ ] API endpoint (FastAPI wrapper for programmatic access)
- [ ] Integration with PostGIS / BigQuery for direct database push

---

## Contributing

Contributions welcome. Open an issue or submit a PR.

```bash
# Fork → Clone → Branch → Code → Test → PR
git checkout -b feature/your-feature
```

---

## Author

**Mahardi Setyoso Pratomo**

Product Operations background with 8+ years in geospatial systems, IoT, and central map operations. Building tools at the intersection of mapping ops and data engineering.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mahardi-setyoso-pratomo-5ab97432/)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?logo=github&logoColor=white)](https://github.com/mahardisetyoso)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?logo=gmail&logoColor=white)](mailto:mahardisetyoso@gmail.com)

---

## License

MIT License — see [LICENSE](LICENSE) for details.