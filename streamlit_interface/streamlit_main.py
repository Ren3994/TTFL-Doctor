import streamlit as st
import importlib
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import STREAMLIT_PAGES_PATH
from update_manager.file_manager import cleanup_db
from update_manager.injury_report_manager import update_injury_report
from update_manager.nba_api_manager import update_nba_data
from data.sql_functions import update_tables

# --- Get page data from /streamlit_pages/ ---
pages_list = []
for filename in os.listdir(STREAMLIT_PAGES_PATH):
    if filename.endswith(".py") and not filename.startswith("_"):
        module_name = filename[:-3]
        module = importlib.import_module(f"streamlit_interface.streamlit_pages.{module_name}")
        title = getattr(module, "TITLE", module_name.replace("_", " ").title())
        order = getattr(module, "ORDER", 999)
        pages_list.append((order, title, module))

pages_list.sort(key=lambda x: (x[0], x[1]))
PAGES = {title: module for _, title, module in pages_list}

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide")
    
# --- Sidebar navigation ---
st.sidebar.title("Navigation")
if st.sidebar.button("🛑 Quitter"):
    cleanup_db()
    os.kill(os.getpid(), signal.SIGTERM)

# --- Trigger updates if needed ---
if "data_ready" not in st.session_state:
    st.session_state.data_ready = False

if not st.session_state.data_ready:
    st.title('🏀 TTFL Doctor')
    with st.spinner('Mise à jour des données'):
        progress = st.progress(0)
        status = st.empty()
        status.text("Injury report :\nDonnées NBA :\nTables de calculs :")
        update_injury_report()
        status.text("Injury report : ✅\nDonnées NBA : \nTables de calculs :")
        progress.progress(10/100)
        update_nba_data(progress=progress, status=status)
        status.text("Injury report : ✅\nDonnées NBA : ✅\nTables de calculs :")
        update_tables(progress)
        status.text("Injury report : ✅\nDonnées NBA : ✅\nTables de calculs : ✅")

        st.session_state.data_ready = True
    st.rerun()

# --- Or show the pages with updated data and a button to update data ---
else:
    if st.sidebar.button("Mettre à jour les données"):
        st.session_state.data_ready = False
        st.rerun()

    selection = st.sidebar.radio("Aller à", list(PAGES.keys()))

    # --- Run the selected page ---
    page = PAGES[selection]
    if hasattr(page, "run"):
        page.run()
    else:
        st.warning(f"The module `{page.__name__}` has no `run()` function.")