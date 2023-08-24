import folium
import pandas as pd
import geopandas as gpd
import numpy as np
import streamlit as st
from polygeohasher import polygeohasher
from streamlit_folium import st_folium

string = st.text_input('Please copy paste your Geohash separated by comma here','qqggtv,qqguxu,qqggu7,qquhch')
data_list = string.split(',')
df = pd.DataFrame(data_list)
df.columns = ['geohash']
geohash_df_list = polygeohasher.geohashes_to_geometry(df,'geohash')
gpd_geohash_geom = gpd.GeoDataFrame(geohash_df_list, geometry = geohash_df_list['geometry'], crs = "EPSG:4326")
geojson_geohash = gpd_geohash_geom.to_json()
m = folium.Map(location=[-6.176366101082727, 106.85262129873658],zoom_start=14)
folium.GeoJson(
     geojson_geohash, 
     name="geohash",
     tooltip = folium.GeoJsonTooltip(fields = ['geohash']),
     style_function = lambda x: {
        'color': 'red',
        'weight': 4,
        'interactive' : True
    }).add_to(m)
st_data = st_folium(m, width=1200, height=800)