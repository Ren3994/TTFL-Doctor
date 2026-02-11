import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from streamlit_interface.streamlit_utils import SEO, config, vspace, get_sc, custom_button_css, st_image_crisp, custom_CSS
from misc.misc import RESIZED_LOGOS_PATH, TEAM_STATS_COLUMN_DEF, CONFERENCES
from streamlit_interface.streamlit_update_manager import update_all_data
from streamlit_interface.session_state_manager import init_session_state
from streamlit_interface.team_stats_utils import *
from streamlit_interface.sidebar import sidebar

# ---------- Initialize session state ----------
PAGENAME = 'stats_equipes'
update_all_data()
init_session_state(page=PAGENAME)
sidebar(page=PAGENAME)
config(page=PAGENAME)
sc = get_sc()

# ---------- UI ----------
st.markdown(custom_CSS, unsafe_allow_html=True)
st.markdown('<div class="date-title">Statistiques des équipes</div>', unsafe_allow_html=True)
vspace()

cont_team_buttons = st.container(horizontal_alignment='center')
conf = st.session_state.get('conf_selector', 'Global')
if conf != 'Global':
    team_list = CONFERENCES[conf.split(' ')[1]]
else:
    team_list = CONFERENCES['Ouest'] + CONFERENCES['Est']

session_state_vars = []

if st.session_state.mobile_layout:
    items_per_row = 5
else:
    items_per_row = 10

for i in range(0, len(team_list), items_per_row):
    row_teams = team_list[i:i+items_per_row]
    cont_row = cont_team_buttons.container(horizontal=True, horizontal_alignment='center')
    vspace(container=cont_team_buttons)
    for team in row_teams:
        cont_team = cont_row.container(gap=None, width=60)
        logo = st_image_crisp(os.path.join(RESIZED_LOGOS_PATH, f"{team}.png"), raw = True)
        st.session_state.setdefault(f"team_stats_button_{team}", False)
        session_state_vars.append(st.session_state[f"team_stats_button_{team}"])
        with cont_team.container():
            with sc(key=f"team_stats_button_key_{team}", css_styles=custom_button_css(
                st.session_state[f"team_stats_button_{team}"], 
                min_width=60)):
                st.button(f'![icon](data:image/png;base64,{logo}) {team}', 
                                          key=f'button_nuit_{team}', 
                                          width=60,
                                          on_click=lambda k=team: st.session_state.update(
                                                   {f"team_stats_button_{k}": 
                                                    not st.session_state[f"team_stats_button_{k}"]}))
vspace()

cont_options = st.container(horizontal_alignment='right', horizontal=True)
cont_options.write('')
cont_options.segmented_control('Conference', ['Global', 'Conférence Ouest', 'Conférence Est'], 
                                      label_visibility='collapsed', default='Global', key='conf_selector')
if cont_options.button('Clear'):
    clear_team_stats_vars()
    st.rerun()
color_cells = cont_options.checkbox('Colorer les cases', key='team_stats_color_cells')
cont_options.write('')

true_vars = [i for i, val in enumerate(session_state_vars) if val]
selected_teams = [team_list[i] for i in true_vars]
team_stats = get_team_stats(selected_teams=selected_teams)

for table in team_stats:
    df = get_teams_from_conf(team_stats[table], st.session_state.conf_selector, table)
    
    with st.expander(table, expanded=any(true_vars)):

        show_df = df
        negative_cols = ['L', 'TOV', 'DRtg', 'TM_TOV_PCT', 'BLKA', 'avg_opp_TTFL', 'rel_opp_avg_TTFL',
                         'pts', 'ast', 'reb', 'Oreb', 'Dreb', 'stl', 'blk', 'opp_FGM', 'opp_FGA', 
                         'opp_FG3M', 'opp_FG3A', 'opp_FTM', 'opp_FTA', 'opp_FT_PCT', 'opp_FG_PCT',
                         'opp_FG3_PCT', 'opp_EFG', 'opp_TS']
        positive_in_df = [col for col in df.columns if col not in negative_cols and col not in ['teamTricode', 'rank']]
        negative_in_df = [col for col in df.columns if col in negative_cols and col not in ['teamTricode', 'rank']]
        
        if color_cells:
            show_df = (df.style
                       .background_gradient(
                            subset=positive_in_df,
                            cmap="YlGn")
                       .background_gradient(
                            subset=negative_in_df,
                            cmap="YlGn_r"))
            
        st.dataframe(show_df, height='content', hide_index=True,
                    column_config={stat : (
                        st.column_config.NumberColumn(
                        TEAM_STATS_COLUMN_DEF[stat]['display'],
                        width = TEAM_STATS_COLUMN_DEF[stat]['width'],
                        format = TEAM_STATS_COLUMN_DEF[stat]['format'],
                        help = TEAM_STATS_COLUMN_DEF[stat]['help'])
                        if TEAM_STATS_COLUMN_DEF[stat]['col'] == 'num' else 
                        st.column_config.TextColumn(
                        TEAM_STATS_COLUMN_DEF[stat]['display'],
                        width = TEAM_STATS_COLUMN_DEF[stat]['width'],
                        help = TEAM_STATS_COLUMN_DEF[stat]['help']))
                        for stat in df})
        
with st.expander('Évolution du classement', expanded=False):
    fig = standings_progress_plot()
    st.plotly_chart(fig)

vspace(30)

SEO('footer')