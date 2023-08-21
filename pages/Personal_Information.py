import streamlit as st

st.title("ABOUT ME")
from PIL import Image

image = Image.open('pages/sample_1.jpg')
st.image(image, width= 400)

st.write("Mahardi Setyoso Pratomo")
st.write("Linkedin [link](https://www.linkedin.com/in/mahardi-setyoso-pratomo-5ab97432/)")
st.write("Github [link](https://github.com/mahardisetyoso)")
st.write("Email: [mahardisetyoso@gmail.com]")