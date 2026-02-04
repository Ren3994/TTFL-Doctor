import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, get_sc, custom_error, st_image_crisp, custom_button_css, custom_CSS
from misc.misc import RESIZED_LOGOS_PATH, IMG_CHARGEMENT, IMG_PLUS_DE_GRAPHES
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.plotting_utils import generate_all_plots
from streamlit_interface.resource_manager import conn_db
from streamlit_interface.classement_TTFL_utils import *
from data.sql_functions import get_games_for_date
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'classement'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)
conn = conn_db()
sc = get_sc()

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Classement TTFL du jour</div>', unsafe_allow_html=True)

if st.session_state.mobile_layout:
    cont = st.container(horizontal_alignment='center', gap='medium')
    cont_date_obj = cont.container(horizontal=True, horizontal_alignment='center')
    cont_left = cont.container(horizontal_alignment='center')
    cont_checkboxes = cont_left.container(horizontal_alignment='center')
    cont_right = cont.container(horizontal_alignment='center')
    games_per_row = 2
    button_fontsize = 13
    button_width = 200
else:
    cont = st.container(horizontal=True, horizontal_alignment='center', gap="small")
    cont_left = cont.container(horizontal_alignment='center', width=300)
    cont_center = cont.container(horizontal_alignment='center')
    cont_right = cont.container(horizontal_alignment='center', width=300)
    cont_checkboxes = cont_left.container()
    cont_date_obj = cont_center.container(horizontal=True, horizontal_alignment='center')
    games_per_row = 4
    button_fontsize = 18
    button_width = 220

if ((st.session_state.local_instance) or
    (st.session_state.get('username', '') != '') or
    (st.session_state.get('temp_jdp_df', False))):
        filter_JDP = cont_checkboxes.checkbox("Masquer les joueurs déjà pick", value=True)
else:
    filter_JDP = cont_checkboxes.checkbox("Masquer les joueurs déjà pick", 
                                value=False, 
                                disabled=True, 
                                help=("Rentrez des picks dans la page "
                                "\"Historique des picks\" pour pouvoir les filtrer")
                            )

filter_inj = cont_checkboxes.checkbox("Masquer les joueurs blessés", value=False)

if cont_left.button('Générer plus de graphes'):
    st.session_state.plot_calc_start += st.session_state.plot_calc_incr
    st.session_state.plot_calc_stop += st.session_state.plot_calc_incr

cont_date_obj.button("◀️", on_click=prev_date)

cont_date_obj.text_input(
    label="date du jour",
    key="date_text",
    on_change=on_text_change,
    label_visibility="collapsed",
    width=120)
if st.session_state.get("text_parse_error", False):
    custom_error('Format invalide<br>JJ/MM/AAAA', fontsize=13, container=cont_center)
        
cont_date_obj.button("▶️", on_click=next_date)

cont_right.markdown(get_low_game_count(conn, st.session_state.date_text), unsafe_allow_html=True)
deadline = get_deadline(conn, st.session_state.date_text)
cont_right.markdown(deadline, unsafe_allow_html=True)
# cont_right.toggle('Traduire les détails des blessures', key='bool_translate')
# limit_reached, _ = deepl_api_limit_reached()
# translate_col = []
# if not limit_reached:
#     if st.session_state.bool_translate:
#         translate_col = ['details']

st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)
vspace()

# Display tonight's games
games_for_date = get_games_for_date(conn, st.session_state.date_text).to_dict(orient="records")
cont_games_tonight = st.container(horizontal_alignment='center',
                                  key=st.session_state.date_text, 
                                  gap='medium')
cont_games_tonight.empty()

for i in range(0, len(games_for_date), games_per_row):
    row_games = games_for_date[i:i + games_per_row]
    row_cont = cont_games_tonight.container(horizontal=True, 
                                            horizontal_alignment='center', 
                                            width=int(len(row_games) * button_width),
                                            key=f'{i}{st.session_state.date_text}')
    row_cont.empty()
    for game in row_games:

        ha = [game["homeTeam"], game["awayTeam"]]
        idx = f'{ha[0]}-{ha[1]}'
        logos = [st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, 
                                             f"{team}.png"), raw=True) for team in ha]

        st.session_state.setdefault(f"classement_{idx}", False)

        if ha[0] == 'TBD' or ha[1] == 'TBD':
            st.session_state.games_TBD = True
        btn_text = (
                    f'![icon](data:image/png;base64,{logos[0]})'
                    f'&nbsp;&nbsp;&nbsp;{ha[0]} - {ha[1]}&nbsp;&nbsp;&nbsp;'
                    f'![icon](data:image/png;base64,{logos[1]})'
                )

        with row_cont:
            with sc(f"custom_button_css_{idx}",  css_styles=custom_button_css(
                st.session_state[f"classement_{idx}"], fontsize=button_fontsize)):
                    st.button(btn_text,
                              key=f"btn_{idx}",
                              width=button_width,
                              on_click=lambda k=idx: st.session_state.update(
                            {f"classement_{k}": not st.session_state[f"classement_{k}"]}))
vspace()

if len(games_for_date) > 0:
    st.markdown("<hr style='width:100%;margin:auto;margin-top:0.2rem;'>", unsafe_allow_html=True)

vspace()
# Display the TTFL table
if st.session_state.topTTFL_df.empty:
    if not st.session_state.games_TBD:
        st.subheader(f"Pas de matchs NBA le {st.session_state.date_text}")
    else:
        st.subheader(f"Les équipes de des matchs du {st.session_state.date_text}" 
                     "n'ont pas encore été déterminées")

else:
    statusholder = st.empty()
    tableholder = st.empty()
    temp_table = st.empty()
    
    if ('plots' not in st.session_state.topTTFL_df or
        st.session_state.plot_calc_start != 0 or
        (st.session_state.topTTFL_df.loc[
            st.session_state.plot_calc_start:
            st.session_state.plot_calc_stop - 1,
            'plots'] == IMG_CHARGEMENT).any()
        ):
        with st.spinner('Génération des graphes...'):        
            if st.session_state.plot_calc_start == 0:
                st.session_state.topTTFL_df['plots'] = IMG_PLUS_DE_GRAPHES
                        
            st.session_state.topTTFL_df.loc[
                st.session_state.plot_calc_start:
                st.session_state.plot_calc_stop - 1, 'plots'] = IMG_CHARGEMENT

            topTTFL_html = df_to_html(st.session_state.topTTFL_df)#, translate_cols=translate_col)
            temp_table.markdown(topTTFL_html, unsafe_allow_html=True)

            start = st.session_state.plot_calc_start
            stop = min(len(st.session_state.topTTFL_df) - 1, st.session_state.plot_calc_stop)
            
            for i in range(start, stop):
                st.session_state.topTTFL_df.iloc[i] = generate_all_plots(
                                                        st.session_state.topTTFL_df.iloc[i],
                                                        st.session_state.date_text)
                
                if (st.session_state.date_text not in st.session_state.calculated or
                    st.session_state.plot_calc_start != 0):
                    statusholder.progress(min(0.999, 
                        (i+1)/(st.session_state.plot_calc_stop - st.session_state.plot_calc_start)))

    selected_games = []
    for key in list(st.session_state.keys()):
        if key.startswith('classement_'):
            if st.session_state[key]:
                selected_games.append(key[11:])

    st.session_state.display_df = apply_df_filters(conn,
                                           st.session_state.date_text,
                                           st.session_state.plot_calc_start,
                                           st.session_state.plot_calc_stop,
                                        #    st.session_state.bool_translate,
                                           filter_JDP,
                                           filter_inj,
                                           selected_games)
    
    idx_pick = get_idx_pick(st.session_state.display_df, st.session_state.date_text, 'Joueur')
    display_df_html = df_to_html(st.session_state.display_df, 
                                #  translate_cols=translate_col, 
                                 highlight_index=idx_pick)
    
    tableholder.markdown(display_df_html, unsafe_allow_html=True)
    st.session_state.calculated.append(st.session_state.date_text)

    temp_table.empty()
    statusholder.empty()

SEO('footer')