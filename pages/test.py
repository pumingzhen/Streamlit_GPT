import streamlit as st
from streamlit_javascript import st_javascript

import time



test = st.text_input("input:")


if st.button("Set"):
    st_javascript(
        f"localStorage.setItem('test123', JSON.stringify({test}));")
    st.success("Success")

if st.button("load"):
    st.write(f"Load test")
    v = st_javascript(f"JSON.parse(localStorage.getItem('test123'));")
    time.sleep(0.5)
    st.write(v)
    st.success("Success")