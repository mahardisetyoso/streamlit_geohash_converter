import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from polygeohasher import polygeohasher
from shapely.geometry import Polygon
from shapely import wkt
import folium
from streamlit_folium import st_folium

coordinates = st.text_input("PLease enter coordinates","-6.171046259577523, 106.82269788734317 ,-6.180712281012674, 106.8225072511238 ,-6.180295319024069, 106.83230595281657 ,-6.170894634306194, 106.82952266400855 ,-6.171046259577523, 106.82269788734317")
list = [float(x) for x in coordinates.split(',')]

longitude = []
latitude = []

for i in range(len(list)):
    if i % 2 == 0:
         latitude.append(list[i])
    else: 
         longitude.append(list[i])
df = pd.DataFrame(columns=['latitude','longitude'])
df['latitude'] = latitude
df['longitude'] = longitude
df['Name']="polygon"
df['points'] = gpd.points_from_xy(df.longitude, df.latitude)
df_geom = df.groupby('Name').agg(geometry = pd.NamedAgg(column='points', aggfunc = lambda x: Polygon(x.values))).reset_index()
gpd_geom = gpd.GeoDataFrame(df_geom, geometry=df_geom['geometry'], crs="EPSG:4326")
geojson=gpd_geom.to_json()

button = st.number_input('Insert a Geohash number', 3)
number = int(button)
geohash_gdf = polygeohasher.create_geohash_list(gpd_geom, number,inner=False)
geohash_gdf_list = polygeohasher.geohashes_to_geometry(geohash_gdf,"geohash_list")
gpd_geohash_geom = gpd.GeoDataFrame(geohash_gdf_list, geometry=geohash_gdf_list['geometry'], crs="EPSG:4326")
geojson_geohash = gpd_geohash_geom.to_json()

m = folium.Map(location=[-6.176366101082727, 106.85262129873658],zoom_start=14)
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
                                     tooltip = folium.GeoJsonTooltip(fields = ['Name', 'geohash_list']), 
                                     style_function = lambda x:{
                                          'color': 'blue'                                          
                                     }))
st_data = st_folium(m, center = geojson, feature_group_to_add=fg, width=1200, height=800)



csv=gpd_geohash_geom.to_csv()
st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name='geohash_file.csv',
    mime='text/csv',
)


