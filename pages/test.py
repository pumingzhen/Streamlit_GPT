import streamlit as st
from streamlit_javascript import st_javascript
import json
import time


def get_from_local_storage(k, out=[]):
    if k not in st.session_state:
        with st.spinner(f"Load {k}"):
            v = st_javascript(f"JSON.parse(localStorage.getItem('{k}'));")
            time.sleep(0.5)
        return v or out
    else:
        return st.session_state[k]


def set_to_local_storage(k):
    jdata = json.dumps(st.session_state[k])
    st_javascript(
        f"localStorage.setItem('{k}', JSON.stringify({jdata}));")
    st.success("Success")

test = st.text_input("input:", on_change=set_to_local_storage, args=("test_input", ), key="test_input")



load = st.button("load")
if load:
    st.session_state['test'] = get_from_local_storage("test_input")
    st.write(st.session_state['test'])