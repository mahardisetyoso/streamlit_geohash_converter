import folium
import pandas as pd
import geopandas as gpd
import json
import numpy as np
import streamlit as st
from polygeohasher import polygeohasher
from shapely.geometry import Polygon
from shapely import wkt
from streamlit_folium import st_folium
from folium.plugins import Draw
from streamlit_folium import folium_static

try:
    button = st.number_input('Insert a Geohash number')
    number = int(button)

    m = folium.Map([-6.175300560878783, 106.82701205991948],zoom_start=16)
    Draw(export=False).add_to(m)

    c1, c2 = st.columns(2)
    with c1:
        output = st_folium(m, width=1200, height=800)
        geojson_str = json.dumps(output)
        geojson_data = gpd.read_file(geojson_str, driver='GeoJSON')
        gdf = gpd.GeoDataFrame.from_features(geojson_data, crs="EPSG:4326")
        gdf['centroid'] = gdf['geometry'].centroid
        gdf['long'] = gdf.centroid.map(lambda p: p.x)
        gdf['lat'] = gdf.centroid.map(lambda p: p.y)
        row = gdf.iloc[0]
        location = f"{row['lat']},{row['long']}"
        gdf = gdf.drop('centroid', axis = 1)
        geojson=gdf.to_json()

        geohash_gdf = polygeohasher.create_geohash_list(gdf, number,inner=False)
        geohash_gdf_list = polygeohasher.geohashes_to_geometry(geohash_gdf,"geohash_list")
        gpd_geohash_geom = gpd.GeoDataFrame(geohash_gdf_list, geometry=geohash_gdf_list['geometry'], crs="EPSG:4326")
        geojson_geohash = gpd_geohash_geom.to_json()

        folium.GeoJson(
            geojson, 
            name="geojson",
            style_function = lambda x: {
                'color': 'red',
                'weight': 4,
                'interactive' : True
            }).add_to(m)

    # Add the geohash layer on top of the drawing polygon layer
        fg = folium.FeatureGroup(name="Geohash")
        fg.add_child(folium.features.GeoJson(geojson_geohash,
                                tooltip = folium.GeoJsonTooltip(fields = ['geohash_list']), 
                                style_function = lambda x:{
                                                'color': 'blue'                                   
                                            })).add_to(m)

    with c2:
        output = st_folium(m, feature_group_to_add=fg, center = location, width=1200, height=800)

    csv=gpd_geohash_geom.to_csv()
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='geohash_file.csv',
     mime='text/csv',
    )

except (TypeError, NameError, AttributeError):
  pass
