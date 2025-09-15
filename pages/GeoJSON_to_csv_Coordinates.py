import pandas as pd
import geopandas as gpd
import streamlit as st

try:
    col_name = st.text_input('Please input Polygon Arena Name column that want to be converted as Coordinate Separated Comma')
    uploaded_files = st.file_uploader("Choose a Geojson file And Please dissolve the Files into single polygon/attribute, Other than that will cause major ERROR!!", accept_multiple_files=False)
    gdf = gpd.read_file(uploaded_files)
    xy = gdf.get_coordinates()
    df_area = gdf[col_name]
    merge_df = pd.concat([df_area, xy], axis=1, join='outer')
    merge_df['concat'] = merge_df['y'].astype(str) + ',' + merge_df['x'].astype(str)
    groupby = merge_df.groupby(col_name).agg({'concat':','.join}).reset_index().reindex(columns=merge_df.columns).drop(['x','y'], axis=1)
    st.dataframe(groupby)
    csv=groupby.to_csv()
    save = st.text_input('Write you files name here and press ENTER!!')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=save + '.csv',
        mime='text/csv',
    )
except (TypeError, NameError, AttributeError):
  pass


