import folium
import geopandas as gpd
import json
import numpy as np
import streamlit as st
from polygeohasher import polygeohasher
from shapely.geometry import Polygon
from shapely import wkt
from streamlit_folium import st_folium

try:
  CENTER_START = [-6.189991467509655, 106.84617273604809]

  #TO DEFINE SESSION STATE
  if "center" not in st.session_state:
    st.session_state["center"] = [-6.189991467509655, 106.84617273604809]

  uploaded_files = st.file_uploader("Choose a Geojson file And Please dissolve the Files into single polygon/attribute, Other than that will cause major ERROR!!", accept_multiple_files=False)
  button = st.number_input('Insert a Geohash number')
  number = int(button)



  gdf = gpd.read_file(uploaded_files)
  gpd_geom = gpd.GeoDataFrame(gdf, geometry=gdf['geometry'], crs="EPSG:4326")
  geojson=gpd_geom.to_json()

  gpd_geom['Center_point'] = gpd_geom['geometry'].centroid
  gpd_geom["lat"] = gpd_geom.Center_point.map(lambda p: p.y)
  gpd_geom["long"] = gpd_geom.Center_point.map(lambda p: p.x)

  try:
    latitude = float(gpd_geom["lat"])
    longitude = float(gpd_geom["long"])
  except ValueError:
    latitude = None
    longitude = None

  if latitude is None or longitude is None:
    st.error("Invalid latitude or longitude value. Please enter valid latitude and longitude values separated by a comma.")
  else:
    st.success("Successfully converted latitude and longitude values to float.")

  st.session_state["center"] = [latitude, longitude]

  geohash_gdf = polygeohasher.create_geohash_list(gdf, number,inner=False)
  geohash_gdf_list = polygeohasher.geohashes_to_geometry(geohash_gdf,"geohash_list")
  gpd_geohash_geom = gpd.GeoDataFrame(geohash_gdf_list, geometry=geohash_gdf_list['geometry'], crs="EPSG:4326")
  geojson_geohash = gpd_geohash_geom.to_json()

  m = folium.Map(location=st.session_state["center"],zoom_start=12)
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

  tiles = ['Cartodb Positron','openstreetmap','Cartodb dark_matter']
  for tile in tiles:
    folium.TileLayer(tile).add_to(m)

  folium.LayerControl().add_to(m)
  st_folium(m, width=1200, height=800)



  csv=gpd_geohash_geom.to_csv()
  st.download_button(
      label="Download data as CSV",
      data=csv,
      file_name='geohash_file.csv',
      mime='text/csv',
  )
except (TypeError, NameError, AttributeError):
  pass


