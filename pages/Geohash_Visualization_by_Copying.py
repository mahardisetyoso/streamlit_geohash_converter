import re
import io
import zipfile
import folium
import pandas as pd
import geopandas as gpd
import streamlit as st
from folium.plugins import MarkerCluster
from polygeohasher import polygeohasher
from streamlit_folium import st_folium

st.set_page_config(page_title="Geohash Visualizer", layout="wide")

CENTER_FALLBACK = [-6.175337169759785, 106.82713616185086]
VALID_RE = re.compile(r"^[0123456789bcdefghjkmnpqrstuvwxyz]+$")  # alfabet geohash (tanpa a/i/l/o)

# -------------------- Helpers --------------------
def clean_and_tokenize(text: str):
    """
    - Lowercase
    - Semua whitespace / ';' -> koma
    - Trim spasi di sekitar koma
    - Split koma -> list
    - Validasi alfabet geohash, panjang 1..12
    - Dedup (preserve order)
    """
    if not text:
        return []
    s = text.lower()
    s = re.sub(r"[;\s]+", ",", s)      # semua whitespace/; -> koma
    s = re.sub(r"\s*,\s*", ",", s)     # trim spasi di sekitar koma
    parts = s.split(",")
    out, seen = [], set()
    for p in parts:
        if p and VALID_RE.match(p) and (1 <= len(p) <= 12) and p not in seen:
            seen.add(p)
            out.append(p)
    return out

# Palet warna diskrit untuk precision 1..12
PRECISION_COLORS = {
    1:"#1f77b4", 2:"#ff7f0e", 3:"#2ca02c", 4:"#d62728",
    5:"#9467bd", 6:"#8c564b", 7:"#e377c2", 8:"#7f7f7f",
    9:"#bcbd22", 10:"#17becf", 11:"#a55194", 12:"#393b79"
}

# -------------------- UI --------------------
st.title("Geohash Visualization by Copy-Paste")

example = (
    "qqguyu7,qqguyur,qqguyu4,qqguygg,qqguyu1,qqguygr,qqguyff,qqguyuq,"
    "qqguz50,qqguyfu,qqguz52,qqguyun,qqguygm,qqguygu,qqguyg7,qqguygq"
)
text = st.text_area(
    "Paste geohash di sini (boleh kolom/komaan/campur newline). "
    "Akan dibersihkan: lowercase, tanpa spasi, alfabet valid, dedup.",
    value=example, height=180,
)

with st.sidebar:
    st.header("Pengaturan Tampilan")
    vis_mode = st.radio(
        "Mode visualisasi", 
        options=["Polygons", "Centroid markers (cluster)"], 
        index=0
    )
    color_mode = st.selectbox(
        "Warna", 
        options=["Single color", "By precision length"], 
        index=1
    )
    base_color = st.color_picker("Warna default (untuk Single color)", "#d62728")
    fill_polygon = st.checkbox("Isi polygon (fill)", value=False)
    weight = st.slider("Garis (weight)", 1, 6, 2)
    opacity = st.slider("Opacity garis", 0.1, 1.0, 1.0, step=0.1)
    fill_opacity = st.slider("Opacity fill", 0.0, 1.0, 0.25, step=0.05)
    max_polys = st.number_input(
        "Batas render polygon (untuk performa di peta)", min_value=100, max_value=20000, value=5000, step=100
    )

    st.markdown("---")
    st.subheader("Export")
    compress_zip = st.checkbox("Compress ke .zip saat download", value=True)
    # Ekspor selalu semua polygon (bukan subset), sesuai permintaan

# -------------------- Preprocess --------------------
geohashes = clean_and_tokenize(text)

colA, colB, colC = st.columns(3)
with colA:
    st.metric("Chars input (raw)", len(text))
with colB:
    st.metric("Geohash valid & unik", len(geohashes))
with colC:
    st.write("Contoh 10 geohash:")
    st.code(", ".join(geohashes[:10]) if geohashes else "-", language="text")

if not geohashes:
    st.warning("Tidak ada geohash valid setelah pembersihan. Cek input.")
    m = folium.Map(location=CENTER_FALLBACK, zoom_start=12)
    st_folium(m, width=1200, height=800)
    st.stop()

df = pd.DataFrame({"geohash": geohashes})

# -------------------- Geometries --------------------
try:
    geohash_df_list = polygeohasher.geohashes_to_geometry(df, "geohash")
except Exception as e:
    st.error(f"Gagal mengonversi geohash ke polygon: {e}")
    m = folium.Map(location=CENTER_FALLBACK, zoom_start=12)
    st_folium(m, width=1200, height=800)
    st.stop()

gdf = gpd.GeoDataFrame(geohash_df_list, geometry=geohash_df_list["geometry"], crs="EPSG:4326")
if gdf.empty or gdf.geometry.is_empty.all():
    st.error("Geometry kosong setelah konversi.")
    m = folium.Map(location=CENTER_FALLBACK, zoom_start=12)
    st_folium(m, width=1200, height=800)
    st.stop()

# Tambah kolom precision (panjang geohash)
gdf["precision"] = gdf["geohash"].astype(str).str.len()

# Center ke centroid union
try:
    centroid = gdf.unary_union.centroid
    center = [float(centroid.y), float(centroid.x)]
except Exception:
    center = CENTER_FALLBACK

# -------------------- Map --------------------
m = folium.Map(location=center, zoom_start=14)

if vis_mode == "Polygons":
    # Demi performa tampilan peta, batasi render. (Ekspor tetap semua polygon.)
    if len(gdf) > max_polys:
        st.info(f"Render di peta dibatasi {max_polys} dari {len(gdf)} polygon demi performa. "
                f"Namun file yang diunduh tetap berisi **SEMUA** polygon.")
        gdf_render = gdf.iloc[:max_polys].copy()
    else:
        gdf_render = gdf

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
        data=gdf_render.to_json(),
        name="geohash-polygons",
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields),
        style_function=style_fn,
        control=True,
        embed=False,
        zoom_on_click=False,
        highlight_function=lambda _: {"weight": weight + 1},
    ).add_to(m)

else:
    # Centroid markers + cluster
    mc = MarkerCluster(name="geohash-centroids", show=True)
    for _, row in gdf.iterrows():
        c = row.geometry.centroid
        folium.Marker(
            location=[c.y, c.x],
            tooltip=f"geohash: {row['geohash']} | precision: {row['precision']}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(mc)
    mc.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

st_folium(
    m,
    center=center,
    width=1200,
    height=800,
)

# -------------------- DOWNLOADS --------------------
# 1) GeoJSON POLYGONS (SELALU SEMUA POLYGON)
#    Terlepas dari subset yg dirender di peta, ekspor pakai seluruh gdf.
polygons_geojson_bytes = gdf.to_json().encode("utf-8")
polygons_fname_json = "geohash_polygons_ALL.geojson"
polygons_fname_zip = "geohash_polygons_ALL.zip"

# 2) GeoJSON CENTROIDS (selalu semua titik centroid dari semua polygon)
cent = gdf.copy()
cent["geometry"] = cent.geometry.centroid
centroids_geojson_bytes = cent[["geohash", "precision", "geometry"]].to_json().encode("utf-8")
centroids_fname_json = "geohash_centroids_ALL.geojson"
centroids_fname_zip = "geohash_centroids_ALL.zip"

def make_zip_bytes(inner_filename: str, inner_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, inner_bytes)
    buf.seek(0)
    return buf.read()

st.subheader("Download Data")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Polygons (ALL)**")
    if compress_zip:
        zip_bytes = make_zip_bytes(polygons_fname_json, polygons_geojson_bytes)
        st.download_button(
            "⬇️ Download Polygons (ZIP)",
            data=zip_bytes,
            file_name=polygons_fname_zip,
            mime="application/zip",
            help="Semua polygon disimpan sebagai GeoJSON di dalam file ZIP."
        )
    else:
        st.download_button(
            "⬇️ Download Polygons (GeoJSON)",
            data=polygons_geojson_bytes,
            file_name=polygons_fname_json,
            mime="application/geo+json",
            help="Semua polygon sebagai GeoJSON."
        )

with col2:
    st.markdown("**Centroids (ALL)**")
    if compress_zip:
        zip_bytes_c = make_zip_bytes(centroids_fname_json, centroids_geojson_bytes)
        st.download_button(
            "⬇️ Download Centroids (ZIP)",
            data=zip_bytes_c,
            file_name=centroids_fname_zip,
            mime="application/zip",
            help="Semua centroid disimpan sebagai GeoJSON di dalam file ZIP."
        )
    else:
        st.download_button(
            "⬇️ Download Centroids (GeoJSON)",
            data=centroids_geojson_bytes,
            file_name=centroids_fname_json,
            mime="application/geo+json",
            help="Semua centroid sebagai GeoJSON."
        )

# -------------------- Utilitas: geohash bersih --------------------
clean_joined = ",".join(geohashes)
with st.expander("Lihat/Salin geohash yang sudah dibersihkan (tanpa spasi, dipisah koma)"):
    st.code(clean_joined, language="text")
    st.download_button(
        "Download geohash_bersih.txt",
        data=clean_joined,
        file_name="geohash_bersih.txt",
        mime="text/plain",
    )
