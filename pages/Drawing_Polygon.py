# Define map
import folium
import json
import io
import streamlit as st
import geopandas as gpd
# import pyperclip  # tidak dipakai untuk clipboard browser
from polygeohasher import polygeohasher
from shapely.geometry import Polygon
from streamlit_folium import st_folium
from folium.plugins import Geocoder 
from newdraw import NewDraw
from shapely import wkt
import pandas as pd
import re

st.set_page_config(page_title="Draw → Geohash", layout="wide")

# --- helper: validasi geohash (alfabet base32 tanpa a/i/l/o) ---
VALID_RE = re.compile(r"^[0123456789bcdefghjkmnpqrstuvwxyz]+$")

def normalize_and_validate_series(s):
    """Terima Series berisi geohash (string). Bersihkan & buang yang invalid."""
    s = s.astype(str).str.strip().str.lower()
    s = s[s.str.len().between(1, 12)]
    s = s[s.apply(lambda x: bool(VALID_RE.match(x)))]
    return s.dropna()

gpd_geohash_geom = None  # inisialisasi agar aman dipakai setelah try/except

try:
    # Precision geohash
    number = int(st.number_input('Geohash precision (1-12)', min_value=1, max_value=12, value=6, step=1))

    # Base map
    m = folium.Map(location=[-6.169689493684541, 106.82936319156342],
                   zoom_start=12,  # perbaikan dari zoom_control=12
                   zoom_control=True)

    # FeatureGroup untuk gambar
    draw_group = folium.FeatureGroup(name='Drawings', show=True, overlay=True, control=True)
    draw_group.add_to(m)

    # Geocoder
    Geocoder(add_marker=True).add_to(m)

    # Draw control yang diarahkan ke FeatureGroup di atas
    NewDraw(edit_options={'featureGroup': draw_group.get_name()}).add_to(m)

    # Tiles
    tiles = ['Cartodb Positron', 'OpenStreetMap', 'CartoDB Dark_Matter']
    for tile in tiles:
        folium.TileLayer(tile).add_to(m)

    # Layer control
    folium.LayerControl(position='bottomleft', collapsed=False).add_to(m)

    # Render map dan ambil objek yang diperlukan
    st_data = st_folium(
        m,
        returned_objects=['last_object_clicked', 'all_drawings', 'last_active_drawing'],
        feature_group_to_add=draw_group,
        width=1200,
        height=700,
    )

    # Ambil GeoJSON hasil gambar
    drawings = None
    if isinstance(st_data, dict):
        drawings = st_data.get("all_drawings")

    if not drawings or not drawings.get("features"):
        st.info("Gambar polygon/garis/area di peta terlebih dahulu, lalu hasilnya akan diproses di sini.")
        # berhenti lebih awal supaya tidak error di bawah
        st.stop()

    # Buat GeoDataFrame dari fitur yang digambar
    gdf = gpd.GeoDataFrame.from_features(drawings["features"], crs="EPSG:4326")

    if gdf.empty or gdf.geometry.is_empty.all():
        st.warning("Geometry dari gambar kosong. Coba gambar ulang.")
        st.stop()

    # Buat daftar geohash yang menutupi geometry pada precision "number"
    # inner=False agar coverage di-outer (tergantung kebutuhan kamu)
    geohash_df = polygeohasher.create_geohash_list(gdf, number, inner=False)
    # Biasanya kolom berisi list geohash per fitur, sering bernama 'geohash_list'.
    # Ubah jadi satu kolom 'geohash' baris-per-baris.
    # Sesuaikan nama kolom jika library kamu menghasilkan nama berbeda.
    list_col = 'geohash_list' if 'geohash_list' in geohash_df.columns else 'geohash'
    if list_col == 'geohash':
        # kalau sudah satuan per-baris, lewati explode
        flat_geohash = geohash_df['geohash']
    else:
        flat_geohash = geohash_df[list_col].explode()

    # Bersihkan & validasi
    flat_geohash = normalize_and_validate_series(pd.Series(flat_geohash))
    flat_geohash = flat_geohash.drop_duplicates().reset_index(drop=True)

    if flat_geohash.empty:
        st.error("Tidak ada geohash valid yang dihasilkan dari gambar + precision tersebut.")
        st.stop()

    # Siapkan DF untuk geohashes_to_geometry (harus 1 geohash per baris)
    df_geo = pd.DataFrame({'geohash': flat_geohash})

    # Konversi setiap geohash ke polygon cell
    geohash_gdf_list = polygeohasher.geohashes_to_geometry(df_geo, "geohash")

    gpd_geohash_geom = gpd.GeoDataFrame(
        geohash_gdf_list,
        geometry=geohash_gdf_list['geometry'],
        crs="EPSG:4326"
    )

    # Output string koma
    geohash_output = ",".join(flat_geohash.tolist())

    st.subheader("Hasil Geohash")
    a = st.text_area(
        'Silakan salin geohash list ini (dipisah koma, tanpa spasi):',
        geohash_output,
        height=120
    )
    # Catatan: tidak ada copy-to-clipboard native di Streamlit server → user copy manual.
    st.download_button(
        "⬇️ Download sebagai TXT",
        data=geohash_output.encode("utf-8"),
        file_name="geohash_list.txt",
        mime="text/plain"
    )

    # Tampilkan ringkas
    st.caption(f"Total geohash unik: {len(flat_geohash)} | Precision: {number}")

except Exception as e:
    # Tampilkan error yang lebih informatif
    st.error(f"Terjadi error: {e}")

# ---- Download CSV aman (hanya jika gpd_geohash_geom sudah terisi) ----
if gpd_geohash_geom is not None and not gpd_geohash_geom.empty:
    csv_bytes = gpd_geohash_geom.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download data polygon cell sebagai CSV",
        data=csv_bytes,
        file_name='geohash_cells.csv',
        mime='text/csv',
    )
