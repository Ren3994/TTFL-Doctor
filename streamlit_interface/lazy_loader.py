import streamlit as st

@st.cache_resource(show_spinner=False)
def get_sc():
    from streamlit_extras.stylable_container import stylable_container as sc
    return sc
