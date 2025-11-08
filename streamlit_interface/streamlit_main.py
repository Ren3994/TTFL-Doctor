import streamlit as st
import importlib
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import STREAMLIT_PAGES_PATH
from update_manager.file_manager import cleanup_db

# PAGES = {}
pages_list = []

for filename in os.listdir(STREAMLIT_PAGES_PATH):
    if filename.endswith(".py") and not filename.startswith("_"):
        module_name = filename[:-3]
        module = importlib.import_module(f"streamlit_interface.streamlit_pages.{module_name}")
        title = getattr(module, "TITLE", module_name.replace("_", " ").title())
        order = getattr(module, "ORDER", 999)
        pages_list.append((order, title, module))
        # PAGES[title] = module

pages_list.sort(key=lambda x: (x[0], x[1]))

PAGES = {title: module for _, title, module in pages_list}

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")

if "data_ready" not in st.session_state:
    st.session_state.data_ready = False

# --- Sidebar navigation ---
if st.sidebar.button("🛑 Quitter"):
    cleanup_db()
    os.kill(os.getpid(), signal.SIGTERM)
    
st.sidebar.title("Navigation")

if not st.session_state.data_ready:
    available_pages = ['Menu principal']
else:
    available_pages = list(PAGES.keys())

selection = st.sidebar.radio("Aller à", available_pages)

# --- Run the selected page ---
page = PAGES[selection]
if hasattr(page, "run"):
    page.run()
else:
    st.warning(f"The module `{page.__name__}` has no `run()` function.")
