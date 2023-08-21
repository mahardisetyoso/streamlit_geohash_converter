import folium
import geopandas as gpd
import json
import numpy as np
import streamlit as st
from polygeohasher import polygeohasher
from shapely.geometry import Polygon
from shapely import wkt
from streamlit_folium import st_folium
from folium.plugins import Draw
from streamlit_folium import st_folium


uploaded_files = st.file_uploader("Choose a Geojson file, Other than that will cause major ERROR!!", accept_multiple_files=False)
button = st.number_input('Insert a Geohash number', 3)
number = int(button)



gdf = gpd.read_file(uploaded_files)
gpd_geom = gpd.GeoDataFrame(gdf, geometry=gdf['geometry'], crs="EPSG:4326")
geojson=gpd_geom.to_json()

geohash_gdf = polygeohasher.create_geohash_list(gdf, number,inner=False)
geohash_gdf_list = polygeohasher.geohashes_to_geometry(geohash_gdf,"geohash_list")
gpd_geohash_geom = gpd.GeoDataFrame(geohash_gdf_list, geometry=geohash_gdf_list['geometry'], crs="EPSG:4326")
gpd_geohash_geom = gpd.GeoDataFrame(geohash_gdf_list, geometry=geohash_gdf_list['geometry'], crs="EPSG:4326")
geojson_geohash = gpd_geohash_geom.to_json()

m = folium.Map(location=[-6.175300560878783, 106.82701205991948],zoom_start=16)
folium.GeoJson(
     geojson, 
     name="geojson",
     style_function = lambda x: {
        'color': 'red',
        'weight': 4,
        'interactive' : True
    }).add_to(m)
fg = folium.FeatureGroup(name="Geohash")
fg.add_child(folium.features.GeoJson(geojson_geohash,
                                     tooltip = folium.GeoJsonTooltip(fields = ['geohash_list']), 
                                     style_function = lambda x:{
                                          'color': 'blue'                                          
                                     })).add_to(m)



st_folium(m, feature_group_to_add=fg, width=1200, height=800)



csv=gpd_geohash_geom.to_csv()
st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name='geohash_file.csv',
    mime='text/csv',
)


