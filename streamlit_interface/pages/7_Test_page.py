import streamlit as st
import sys
import os
import datetime
import extra_streamlit_components as stx

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from streamlit_interface.sidebar import sidebar

sidebar(page='test')




st.write("# Cookie Manager")

@st.fragment
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

st.subheader("All Cookies:")
cookies = cookie_manager.get_all()
st.write(cookies)

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Get Cookie:")
    cookie = st.text_input("Cookie", key="0")
    clicked = st.button("Get")
    if clicked:
        value = cookie_manager.get(cookie=cookie)
        st.write(value)
with c2:
    st.subheader("Set Cookie:")
    cookie = st.text_input("Cookie", key="1")
    val = st.text_input("Value")
    if st.button("Add"):
        cookie_manager.set(cookie, val) # Expires in a day by default
with c3:
    st.subheader("Delete Cookie:")
    cookie = st.text_input("Cookie", key="2")
    if st.button("Delete"):
        cookie_manager.delete(cookie)
# st.write(st.context.cookies)
# st.write(st.context.headers)
# st.write(st.context.ip_address)


# cookies = get_manager()
# cont = st.container(horizontal=True)
# cont2 = st.container(horizontal=True)

# st.write(cookies)

# cont.text_input('key', key='cookie_key', width=100)
# cont.text_input('value', key='cookie_value', width=100)

# if cont.button('rerun'):
#     st.rerun()

# if cont.button('Set'):
#     set_cookie(st.session_state.cookie_key, st.session_state.cookie_value)

# if cont.button('Del'):
#     delete_cookie(st.session_state.cookie_key)

# # if cont.button('save2supa + set token'):
#     # token = generate_auth_token()
#     # set_cookie('auth_token', token)
#     # save_user_to_supabase(token)

# if cont.button('check cookies for auth'):
#     check_user_cookies_to_login()