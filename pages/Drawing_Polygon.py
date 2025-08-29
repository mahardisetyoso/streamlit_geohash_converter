import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder, MarkerCluster
from newdraw import NewDraw

import geopandas as gpd
import pandas as pd
import re, json, io, zipfile
from polygeohasher import polygeohasher

st.set_page_config(page_title="Draw → Geohash (Overlay in One Map)", layout="wide")

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

# ---------------- Sidebar / Controls ----------------
st.title("Draw → Geohash (Overlay in One Map)")

colA, colB = st.columns(2)
with colA:
    precision = st.slider("Precision geohash (1 = sel besar … 12 = sel kecil)", 1, 12, 6, 1)
with colB:
    inner_cover = st.checkbox("Inner coverage (strict inside geometry)", value=False)

with st.sidebar:
    st.header("Map Overlay Options")
    color_mode = st.selectbox("Warna cells", ["By precision length", "Single color"], index=0)
    base_color = st.color_picker("Warna default (Single color)", "#d62728")
    fill_polygon = st.checkbox("Isi polygon (fill)", value=False)
    weight = st.slider("Garis (weight)", 1, 6, 2)
    opacity = st.slider("Opacity garis", 0.1, 1.0, 1.0, step=0.1)
    fill_opacity = st.slider("Opacity fill", 0.0, 1.0, 0.25, step=0.05)
    max_cells_on_map = st.number_input("Batas cell ditampilkan (agar ringan)", 100, 20000, 5000, 100)
    show_centroids = st.checkbox("Tampilkan centroid markers (cluster)", value=False)

    st.header("Export")
    compress_zip = st.checkbox("Compress GeoJSON polygons ke .zip", value=True)

# ---------------- Session state to keep drawings ----------------
# Kita simpan FeatureCollection hasil gambar di session_state supaya
# di render map berikutnya dapat ditampilkan lagi dan dihitung cell-nya.
if "features_fc" not in st.session_state:
    st.session_state["features_fc"] = {"type": "FeatureCollection", "features": []}

# ---------------- Build ONE Map (with Draw + Overlay) ----------------
m = folium.Map(location=[-6.169689493684541, 106.82936319156342], zoom_start=12, zoom_control=True)

# FeatureGroup untuk gambar (Draw plugin akan menaruh layer di sini)
draw_group = folium.FeatureGroup(name='Drawings', show=True, overlay=True, control=True).add_to(m)

# Jika sudah ada gambar tersimpan dari session_state, tampilkan kembali di group yang sama
if st.session_state["features_fc"]["features"]:
    folium.GeoJson(
        data=st.session_state["features_fc"],
        name="Drawings (saved)",
        tooltip=folium.GeoJsonTooltip(fields=[]),  # sesuaikan jika ada properti
    ).add_to(draw_group)

# Tambahkan Draw control yang menunjuk ke draw_group
NewDraw(edit_options={'featureGroup': draw_group.get_name()}).add_to(m)

# Geocoder & Tiles
Geocoder(add_marker=True).add_to(m)
for tile in ['CartoDB positron', 'OpenStreetMap', 'CartoDB dark_matter']:
    folium.TileLayer(tile).add_to(m)

# ------ Jika ada gambar tersimpan, hitung cells & overlay di MAP YANG SAMA ------
cells_gdf = None
if st.session_state["features_fc"]["features"]:
    # Build GeoDataFrame dari gambar tersimpan
    gdf = gpd.GeoDataFrame.from_features(st.session_state["features_fc"], crs="EPSG:4326")

    # Pastikan polygon: LineString/Point → buffer kecil (5 m)
    non_poly = ~gdf.geom_type.isin(["Polygon", "MultiPolygon"])
    if non_poly.any():
        gdf_poly = gdf.to_crs(3857)
        gdf_poly.loc[non_poly, "geometry"] = gdf_poly.loc[non_poly, "geometry"].buffer(5)  # 5 meter
        gdf_poly = gdf_poly.to_crs(4326)
    else:
        gdf_poly = gdf

    # Generate geohash list dari gambar tersimpan
    try:
        gh_df = polygeohasher.create_geohash_list(gdf_poly, precision, inner=inner_cover)
        list_col = "geohash_list" if "geohash_list" in gh_df.columns else ("geohash" if "geohash" in gh_df.columns else None)
        if list_col:
            flat = gh_df[list_col].explode() if list_col == "geohash_list" else gh_df[list_col]
            flat = normalize_and_validate_series(pd.Series(flat)).drop_duplicates().reset_index(drop=True)
        else:
            flat = pd.Series([], dtype=str)
    except Exception as e:
        st.error(f"Gagal membuat geohash list: {e}")
        flat = pd.Series([], dtype=str)

    # Jika ada geohash → buat cell polygons & overlay
    if not flat.empty:
        try:
            cells_gdf = polygeohasher.geohashes_to_geometry(pd.DataFrame({"geohash": flat}), "geohash")
            cells_gdf = gpd.GeoDataFrame(cells_gdf, geometry=cells_gdf["geometry"], crs="EPSG:4326")
            cells_gdf["precision"] = cells_gdf["geohash"].astype(str).str.len()
        except Exception as e:
            st.error(f"Gagal membuat GeoJSON polygon sel geohash: {e}")
            cells_gdf = None

        if cells_gdf is not None and not cells_gdf.empty:
            # Limit jumlah cell yang ditampilkan di peta (unduhan tetap semua)
            if len(cells_gdf) > max_cells_on_map:
                st.info(f"Preview cell dibatasi {max_cells_on_map} dari {len(cells_gdf)} untuk performa. Unduhan tetap semua data.")
                cells_preview = cells_gdf.iloc[:max_cells_on_map].copy()
            else:
                cells_preview = cells_gdf

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

            # Overlay cells di MAP YANG SAMA
            folium.GeoJson(
                data=cells_preview.to_json(),
                name="Geohash Cells",
                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields),
                style_function=style_fn,
                control=True,
                embed=False,
                zoom_on_click=False,
                highlight_function=lambda _: {"weight": weight + 1},
            ).add_to(m)

            # Opsional: centroid markers (cluster)
            if show_centroids:
                mc = MarkerCluster(name="Geohash Centroids")
                for _, row in cells_preview.iterrows():
                    c = row.geometry.centroid
                    folium.Marker(
                        location=[c.y, c.x],
                        tooltip=f"geohash: {row['geohash']} | precision: {row['precision']}",
                        icon=folium.Icon(color="blue", icon="info-sign"),
                    ).add_to(mc)
                mc.add_to(m)

# Layer control
folium.LayerControl(position='bottomleft', collapsed=False).add_to(m)

# ---------------- Render ONE MAP (draw + overlay) ----------------
st.subheader("Gambar area & lihat overlay cells pada peta yang sama")
st.caption("Setiap selesai menggambar, aplikasi otomatis rerun → overlay cells diperbarui di map ini.")
st_map = st_folium(
    m,
    width=1200, height=700,
    returned_objects=['last_object_clicked', 'all_drawings', 'last_active_drawing'],
    feature_group_to_add=draw_group,
    key="one_map"
)

# ---------------- Update session_state dengan gambar terbaru ----------------
# Normalisasi keluaran st_folium ke FeatureCollection dan simpan ke session_state
def extract_features(st_data_obj):
    feats = []
    if isinstance(st_data_obj, dict):
        ad = st_data_obj.get("all_drawings")
        if isinstance(ad, list):
            feats = ad
        elif isinstance(ad, dict):
            if ad.get("type") == "FeatureCollection":
                feats = ad.get("features", [])
            elif ad:
                feats = [ad]
    elif isinstance(st_data_obj, list):
        feats = st_data_obj
    return {"type": "FeatureCollection", "features": feats}

fc_new = extract_features(st_map)
# Hanya update jika ada fitur (mencegah mengosongkan saat interaksi lain)
if fc_new["features"]:
    st.session_state["features_fc"] = fc_new

# ---------------- Panel hasil & unduhan ----------------
st.subheader("Hasil & Unduhan")
if st.session_state["features_fc"]["features"]:
    # Hitung ulang daftar geohash dari gambar tersimpan (konsisten dengan overlay)
    gdf_saved = gpd.GeoDataFrame.from_features(st.session_state["features_fc"], crs="EPSG:4326")
    non_poly = ~gdf_saved.geom_type.isin(["Polygon", "MultiPolygon"])
    if non_poly.any():
        gdf_saved = gdf_saved.to_crs(3857)
        gdf_saved.loc[non_poly, "geometry"] = gdf_saved.loc[non_poly, "geometry"].buffer(5)
        gdf_saved = gdf_saved.to_crs(4326)

    try:
        gh_df2 = polygeohasher.create_geohash_list(gdf_saved, precision, inner=inner_cover)
        list_col2 = "geohash_list" if "geohash_list" in gh_df2.columns else ("geohash" if "geohash" in gh_df2.columns else None)
        if list_col2:
            flat2 = gh_df2[list_col2].explode() if list_col2 == "geohash_list" else gh_df2[list_col2]
            flat2 = normalize_and_validate_series(pd.Series(flat2)).drop_duplicates().reset_index(drop=True)
        else:
            flat2 = pd.Series([], dtype=str)
    except Exception as e:
        st.error(f"Gagal membuat geohash list: {e}")
        flat2 = pd.Series([], dtype=str)

    st.caption(f"Precision: {precision} | Total geohash unik: {len(flat2)} | Inner: {inner_cover}")
    joined_comma = ",".join(flat2.tolist())
    st.text_area("Salin geohash (comma-separated, no space):", joined_comma, height=120)

    # TXT (comma)
    st.download_button("⬇️ TXT (comma)", joined_comma.encode("utf-8"), "geohash_list.txt", "text/plain")
    # JSON array
    st.download_button("⬇️ JSON array", json.dumps(flat2.tolist()).encode("utf-8"), "geohash_list.json", "application/json")
    # TXT (newline)
    st.download_button("⬇️ TXT (newline)", "\n".join(flat2.tolist()).encode("utf-8"), "geohash_list_lines.txt", "text/plain")
    # CSV
    st.download_button("⬇️ CSV", flat2.to_frame("geohash").to_csv(index=False).encode("utf-8"), "geohash_list.csv", "text/csv")

    # GeoJSON polygons (ALL), bukan yang dibatasi preview
    try:
        cells_all = polygeohasher.geohashes_to_geometry(pd.DataFrame({"geohash": flat2}), "geohash")
        cells_all = gpd.GeoDataFrame(cells_all, geometry=cells_all["geometry"], crs="EPSG:4326")
        geojson_bytes = cells_all.to_json().encode("utf-8")
        if compress_zip:
            st.download_button(
                "⬇️ GeoJSON polygons (ZIP)",
                make_zip_bytes("geohash_polygons.geojson", geojson_bytes),
                "geohash_polygons.zip",
                "application/zip"
            )
        else:
            st.download_button(
                "⬇️ GeoJSON polygons",
                geojson_bytes,
                "geohash_polygons.geojson",
                "application/geo+json"
            )
    except Exception as e:
        st.error(f"Gagal membuat GeoJSON polygons: {e}")
else:
    st.info("Belum ada gambar untuk dihitung/diunduh.")
