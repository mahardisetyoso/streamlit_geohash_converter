import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder, MarkerCluster
from newdraw import NewDraw

import geopandas as gpd
import pandas as pd
import re, json, io, zipfile
from polygeohasher import polygeohasher

st.set_page_config(page_title="Draw → Geohash Exporter + Preview", layout="wide")

# ---------------- Helpers ----------------
VALID_RE = re.compile(r"^[0123456789bcdefghjkmnpqrstuvwxyz]+$")  # geohash base32 (tanpa a/i/l/o)

def normalize_and_validate_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s[s.str.len().between(1, 12)]
    s = s[s.apply(lambda x: bool(VALID_RE.match(x)))]
    return s.dropna()

def make_zip_bytes(inner_filename: str, inner_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, inner_bytes)
    buf.seek(0)
    return buf.read()

PRECISION_COLORS = {
    1:"#1f77b4", 2:"#ff7f0e", 3:"#2ca02c", 4:"#d62728",
    5:"#9467bd", 6:"#8c564b", 7:"#e377c2", 8:"#7f7f7f",
    9:"#bcbd22", 10:"#17becf", 11:"#a55194", 12:"#393b79"
}

# ---------------- UI ----------------
st.title("Draw → Geohash Exporter + Map Preview")

colA, colB = st.columns(2)
with colA:
    precision = st.slider("Precision geohash (1 = sel besar … 12 = sel kecil)", 1, 12, 6, 1)
with colB:
    inner_cover = st.checkbox("Inner coverage (strict inside geometry)", value=False)

with st.sidebar:
    st.header("Export")
    compress_zip = st.checkbox("Compress GeoJSON polygons ke .zip", value=True)

    st.header("Preview Cells (Map)")
    preview_cells = st.checkbox("Tampilkan preview cell geohash di peta", value=True)
    color_mode = st.selectbox("Warna", ["By precision length", "Single color"], index=0)
    base_color = st.color_picker("Warna default (Single color)", "#d62728")
    fill_polygon = st.checkbox("Isi polygon (fill)", value=False)
    weight = st.slider("Garis (weight)", 1, 6, 2)
    opacity = st.slider("Opacity garis", 0.1, 1.0, 1.0, step=0.1)
    fill_opacity = st.slider("Opacity fill", 0.0, 1.0, 0.25, step=0.05)
    max_preview_polys = st.number_input("Batas render polygon (preview)", 100, 20000, 5000, 100)
    show_centroids = st.checkbox("Tampilkan centroid markers (cluster)", value=False)

# ---------------- Map untuk menggambar ----------------
m_draw = folium.Map(location=[-6.169689493684541, 106.82936319156342], zoom_start=12, zoom_control=True)
draw_group = folium.FeatureGroup(name='Drawings', show=True, overlay=True, control=True).add_to(m_draw)
Geocoder(add_marker=True).add_to(m_draw)
NewDraw(edit_options={'featureGroup': draw_group.get_name()}).add_to(m_draw)

for tile in ['CartoDB positron', 'OpenStreetMap', 'CartoDB dark_matter']:
    folium.TileLayer(tile).add_to(m_draw)
folium.LayerControl(position='bottomleft', collapsed=False).add_to(m_draw)

st.subheader("1) Gambar area di peta ini")
st.caption("Gambar polygon/garis/titik. Setelah selesai menggambar, geohash akan dihitung otomatis.")
st_data = st_folium(
    m_draw,
    width=1200, height=650,
    returned_objects=['last_object_clicked', 'all_drawings', 'last_active_drawing'],
    feature_group_to_add=draw_group,
    key="draw"
)

# ---------------- Ambil hasil gambar ----------------
features = []
if isinstance(st_data, dict):
    ad = st_data.get("all_drawings")
    if isinstance(ad, list):
        features = ad
    elif isinstance(ad, dict):
        if ad.get("type") == "FeatureCollection":
            features = ad.get("features", [])
        elif ad:
            features = [ad]
elif isinstance(st_data, list):
    features = st_data

if not features:
    st.info("Belum ada gambar. Silakan gambar area terlebih dahulu.")
    st.stop()

# ---------------- GeoDataFrame dari gambar ----------------
gdf = gpd.GeoDataFrame.from_features({"type": "FeatureCollection", "features": features}, crs="EPSG:4326")
if gdf.empty or gdf.geometry.is_empty.all():
    st.warning("Geometry kosong. Coba gambar lagi.")
    st.stop()

# Pastikan polygon: LineString/Point → buffer kecil (5 m) agar jadi polygon
non_poly = ~gdf.geom_type.isin(["Polygon", "MultiPolygon"])
if non_poly.any():
    gdf_poly = gdf.to_crs(3857)
    gdf_poly.loc[non_poly, "geometry"] = gdf_poly.loc[non_poly, "geometry"].buffer(5)  # 5 meter
    gdf_poly = gdf_poly.to_crs(4326)
else:
    gdf_poly = gdf

# ---------------- Generate geohash ----------------
try:
    gh_df = polygeohasher.create_geohash_list(gdf_poly, precision, inner=inner_cover)
except Exception as e:
    st.error(f"Gagal membuat geohash list: {e}")
    st.stop()

# Kolom list → explode jadi satu kolom geohash
list_col = "geohash_list" if "geohash_list" in gh_df.columns else ("geohash" if "geohash" in gh_df.columns else None)
if list_col is None:
    st.error("Tidak menemukan kolom geohash/geohash_list pada output polygeohasher.")
    st.write("Kolom tersedia:", gh_df.columns.tolist())
    st.stop()

flat = gh_df[list_col].explode() if list_col == "geohash_list" else gh_df[list_col]
flat = normalize_and_validate_series(pd.Series(flat)).drop_duplicates().reset_index(drop=True)

if flat.empty:
    st.error("Tidak ada geohash valid yang dihasilkan. Ubah precision atau gambar area yang lebih besar.")
    st.stop()

# ---------------- Tampilkan hasil & Download ----------------
st.subheader("2) Hasil Geohash")
st.caption(f"Precision: {precision} | Total geohash unik: {len(flat)} | Inner coverage: {inner_cover}")

joined_comma = ",".join(flat.tolist())
st.text_area("Salin geohash (dipisah koma, tanpa spasi):", joined_comma, height=120)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.download_button(
        "TXT (comma)",
        data=joined_comma.encode("utf-8"),
        file_name="geohash_list.txt",
        mime="text/plain"
    )
with c2:
    st.download_button(
        "JSON array",
        data=json.dumps(flat.tolist()).encode("utf-8"),
        file_name="geohash_list.json",
        mime="application/json"
    )
with c3:
    st.download_button(
        "TXT (newline)",
        data="\n".join(flat.tolist()).encode("utf-8"),
        file_name="geohash_list_lines.txt",
        mime="text/plain"
    )
with c4:
    st.download_button(
        "CSV",
        data=flat.to_frame("geohash").to_csv(index=False).encode("utf-8"),
        file_name="geohash_list.csv",
        mime="text/csv"
    )

# GeoJSON polygons untuk semua sel geohash
cells_gdf = None
geojson_bytes = b""
try:
    cells_gdf = polygeohasher.geohashes_to_geometry(pd.DataFrame({"geohash": flat}), "geohash")
    cells_gdf = gpd.GeoDataFrame(cells_gdf, geometry=cells_gdf["geometry"], crs="EPSG:4326")
    geojson_bytes = cells_gdf.to_json().encode("utf-8")
except Exception as e:
    st.error(f"Gagal membuat GeoJSON polygon sel geohash: {e}")

with c5:
    if geojson_bytes:
        if compress_zip:
            zip_bytes = make_zip_bytes("geohash_polygons.geojson", geojson_bytes)
            st.download_button(
                "GeoJSON (ZIP)",
                data=zip_bytes,
                file_name="geohash_polygons.zip",
                mime="application/zip"
            )
        else:
            st.download_button(
                "GeoJSON",
                data=geojson_bytes,
                file_name="geohash_polygons.geojson",
                mime="application/geo+json"
            )

# ---------------- Preview Cells di Peta ----------------
if preview_cells and cells_gdf is not None and not cells_gdf.empty:
    st.subheader("3) Preview Cell Geohash di Peta")

    # Tambahkan kolom precision length
    cells_gdf["precision"] = cells_gdf["geohash"].astype(str).str.len()

    # Center ke centroid union
    try:
        center_geom = cells_gdf.unary_union.centroid
        center = [float(center_geom.y), float(center_geom.x)]
    except Exception:
        center = [-6.169689493684541, 106.82936319156342]

    # Batasi preview agar ringan
    if len(cells_gdf) > max_preview_polys:
        st.info(f"Preview dibatasi {max_preview_polys} dari {len(cells_gdf)} polygons untuk menjaga performa (unduhan tetap SEMUA data).")
        cells_preview = cells_gdf.iloc[:max_preview_polys].copy()
    else:
        cells_preview = cells_gdf

    # Build map preview
    m_prev = folium.Map(location=center, zoom_start=14, zoom_control=True)
    for tile in ['CartoDB positron', 'OpenStreetMap', 'CartoDB dark_matter']:
        folium.TileLayer(tile).add_to(m_prev)

    # Style function
    if color_mode == "By precision length":
        def style_fn(feat):
            prec = feat["properties"].get("precision", 0)
            col = PRECISION_COLORS.get(int(prec), base_color)
            return {
                "color": col,
                "weight": weight,
                "opacity": opacity,
                "fillColor": col,
                "fillOpacity": fill_opacity if fill_polygon else 0.0,
            }
        tooltip_fields = ["geohash", "precision"]
    else:
        def style_fn(_):
            return {
                "color": base_color,
                "weight": weight,
                "opacity": opacity,
                "fillColor": base_color,
                "fillOpacity": fill_opacity if fill_polygon else 0.0,
            }
        tooltip_fields = ["geohash"]

    folium.GeoJson(
        data=cells_preview.to_json(),
        name="geohash-cells",
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields),
        style_function=style_fn,
        control=True,
        embed=False,
        zoom_on_click=False,
        highlight_function=lambda _: {"weight": weight + 1},
    ).add_to(m_prev)

    # Centroid markers (cluster)
    if show_centroids:
        mc = MarkerCluster(name="centroids")
        for _, row in cells_preview.iterrows():
            c = row.geometry.centroid
            folium.Marker(
                location=[c.y, c.x],
                tooltip=f"geohash: {row['geohash']} | precision: {row['precision']}",
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(mc)
        mc.add_to(m_prev)

    folium.LayerControl(collapsed=False).add_to(m_prev)

    st_folium(
        m_prev,
        width=1200,
        height=650,
        key="preview"
    )
