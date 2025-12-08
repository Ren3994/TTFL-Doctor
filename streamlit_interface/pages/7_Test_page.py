import streamlit as st
import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.sidebar import sidebar

sidebar(page='test')

manager = st.session_state.get('cookie_manager', None)
if manager is not None:
    cookies = manager.get_all(key='rrrrrr')
    st.write(cookies)

# st.write(st.context.cookies)

# st.subheader("All Cookies:")
# cookies = manager.get_all()
# st.write(cookies)

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Get Cookie:")
    cookie = st.text_input("Cookie", key="0")
    clicked = st.button("Get")
    if clicked:
        value = manager.get(cookie=cookie)
        st.write(value)
with c2:
    st.subheader("Set Cookie:")
    cookie = st.text_input("Cookie", key="1")
    val = st.text_input("Value")
    if st.button("Add"):
        manager.set(cookie, val) # Expires in a day by default
with c3:
    st.subheader("Delete Cookie:")
    cookie = st.text_input("Cookie", key="2")
    if st.button("Delete"):
        manager.delete(cookie)

cont=st.container(horizontal=True)
cookie_key = cont.text_input('cookie_key', key='3')
# cookie_val = cont.text_input('cookie_val', key='4')
# cookie_path = cont.text_input('cookie_path', key='5')
# expires = datetime.datetime(1970, 1, 1)
if cont.button('Set custom cookie'):
    manager.set(cookie = 'ttfl-doctor.auth_token',
                val='', 
                path="/~/+", 
                expires_at=datetime.datetime(1970, 1, 1))