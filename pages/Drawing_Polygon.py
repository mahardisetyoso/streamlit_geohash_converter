# Define map
import folium
import json
import streamlit as st
import geopandas as gpd
import pyperclip
from polygeohasher import polygeohasher
from shapely.geometry import Polygon
from streamlit_folium import st_folium
from folium.plugins import Geocoder 
from newdraw import NewDraw
from shapely import wkt

try:
    button = st.number_input('Insert a Geohash number', 3)
    number = int(button) 

    m = folium.Map(location=[-6.169689493684541, 106.82936319156342], zoom_control=12)

    # Define FeatureGroup for drawings
    draw_group = folium.FeatureGroup(name='Drawings', show=True, overlay=True, control=True)
    draw_group.add_to(m)
    Geocoder(add_marker=True).add_to(m)

    # Pass the draw_group internal folium name in edit_options
    NewDraw(
        edit_options={
            'featureGroup': draw_group.get_name(),
        }).add_to(m)
        
    tiles = ['Cartodb Positron','openstreetmap','Cartodb dark_matter']
    for tile in tiles:
        folium.TileLayer(tile).add_to(m)     

    # Optionally, define LayerControl to disable hide the Drawings FeatureGroup
    lc = folium.LayerControl(position='bottomleft', collapsed=False)
    lc.add_to(m)

    # Render the map
    st.session_state["st_data"] = st_folium(m, 
                        width='100%',
                        returned_objects=['last_object_clicked', 'all_drawings', 'last_active_drawing'],
                        feature_group_to_add=draw_group)


    geojson_str = json.dumps(st.session_state["st_data"])
    geojson_data = gpd.read_file(geojson_str, driver='GeoJSON')
    gdf = gpd.GeoDataFrame.from_features(geojson_data, crs="EPSG:4326")
    geohash_gdf = polygeohasher.create_geohash_list(gdf, number,inner=False)
    geohash_gdf_list = polygeohasher.geohashes_to_geometry(geohash_gdf,"geohash_list")
    gpd_geohash_geom = gpd.GeoDataFrame(geohash_gdf_list, geometry=geohash_gdf_list['geometry'], crs="EPSG:4326")
    geohash_output = gpd_geohash_geom['geohash_list'].str.cat(sep=',')

    a=st.text_area('Please copy this geohash list code and use Geohash Visualization for coverage checking', geohash_output)

    if st.button('Copy'):
        pyperclip.copy(a)
        st.success('Text copied successfully!')
except (TypeError, NameError, AttributeError):
  pass

csv=gpd_geohash_geom.to_csv()
st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name='geohash_file.csv',
    mime='text/csv',
)
file_geojson = gpd_geohash_geom.to_json()
  st.download_button(
      label="Download data as JSON",
      data=file_geojson,
      file_name='geohash_file.geojson',
  )


