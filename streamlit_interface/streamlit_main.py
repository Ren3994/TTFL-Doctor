import streamlit as st
import importlib
import signal
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import STREAMLIT_PAGES_PATH

PAGES = {}

for filename in os.listdir(STREAMLIT_PAGES_PATH):
    if filename.endswith(".py") and not filename.startswith("_"):
        module_name = filename[:-3]
        module = importlib.import_module(f"streamlit_interface.streamlit_pages.{module_name}")
        title = getattr(module, "TITLE", module_name.replace("_", " ").title())
        PAGES[title] = module

st.set_page_config(
    page_title="TTFL Doctor",
    page_icon="🏀",
    layout="wide") 

# --- Sidebar navigation ---
if st.sidebar.button("🛑 Quitter"):
    os.kill(os.getpid(), signal.SIGTERM)

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Aller à", list(PAGES.keys()))



# --- Run the selected page ---
page = PAGES[selection]
if hasattr(page, "run"):
    page.run()
else:
    st.warning(f"The module `{page.__name__}` has no `run()` function.")
