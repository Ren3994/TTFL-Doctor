import streamlit as st

def get_palette(key=None):

    palette = {}

    pct_gold = "#FFD700"
    pct_blue = "#1E90FF"
    pct_light_green = (182, 242, 182)
    pct_bright_green = (0, 204, 102)
    pct_light_red = (246, 176, 176)
    pct_bright_red = (255, 77, 77)

    if st.session_state.dark_mode:
        table_hover="#1e2a3b"
        table_text="#C5C5C5"
        table_header_text="#CAC8C8"
        table_header_bkg = "#252b32"
        table_even, table_odd = "#222222", "#111111"
        table_pick = "#82471D"
        table_pick_hover = "#AA622F"
        table_best_pick = "#E1C0029F"
        table_best_pick_hover = "#FFD900A0"
        table_tooltip_bkg = "#2b2b2b"
        table_tooltip_text = "#e0e0e0"
        table_injured = "#CD5050"
        table_injured_hover = "#CF6767"

        button_text = "#FFFFFF"

        button_bkg = '#131720'
        button_bkg_selected = "#44454E" 
        button_hover = '#262831'
        button_hover_selected = "#53555C"
        
        button_pick_bkg = "#82471D"
        button_pick_bkg_selected = "#AA622F"
        button_pick_hover = "#AA622F"
        button_pick_hover_selected = "#C16C2F"
        button_pick_text = "#C5C5C5"

    else:
        table_hover="#CACACA"
        table_text="#434343"
        table_header_text="#4A4A4A"
        table_header_bkg = "#bbc2cd"
        table_even, table_odd = "#efefef", "#E2E2E2"
        table_pick = "#C57842"
        table_pick_hover = "#D37431"
        table_best_pick = "#E1C0029F"
        table_best_pick_hover = "#FFD900A0"
        table_tooltip_bkg = "#E2E2E2"
        table_tooltip_text = "#282828"
        table_injured = "#CD5050"
        table_injured_hover = "#B74F4F"

        button_bkg = "#f3f3f3"
        button_bkg_selected = "#c6cfda"
        button_hover = "#e2e7ee"
        button_hover_selected = "#aab3bf"
        button_text = "#000000"

        button_pick_bkg = table_pick
        button_pick_bkg_selected = table_pick
        button_pick_hover = "#D37431"
        button_pick_hover_selected = table_pick_hover
        button_pick_text = "#434343"

    palette['table'] = {'hover' : table_hover,
                        'text' : table_text,
                        'header_text' : table_header_text,
                        'header_bkg' : table_header_bkg,
                        'even' : table_even,
                        'odd' : table_odd,
                        'pick' : table_pick,
                        'pick_hover' : table_pick_hover,
                        'best_pick' : table_best_pick,
                        'best_pick_hover' : table_best_pick_hover,
                        'tooltip_bkg' : table_tooltip_bkg,
                        'tooltip_text' : table_tooltip_text,
                        'injured' : table_injured,
                        'injured_hover' : table_injured_hover
    }

    palette['button'] = {'text' : button_text,
                         'bkg' : button_bkg,
                         'bkg_selected' : button_bkg_selected,
                         'hover' : button_hover,
                         'hover_selected' : button_hover_selected,
                         'pick_bkg' : button_pick_bkg,
                         'pick_bkg_selected' : button_pick_bkg_selected,
                         'pick_hover' : button_pick_hover,
                         'pick_hover_selected' : button_pick_hover_selected,
                         'pick_text' : button_pick_text
                         }
    
    palette['pct'] = {'gold' : pct_gold, 
                      'blue' : pct_blue,
                      'light_green' : pct_light_green,
                      'bright_green' : pct_bright_green,
                      'light_red' : pct_light_red,
                      'bright_red' : pct_bright_red,
                      'text' : table_tooltip_text
                      }

    if key is None:
        return palette
    else:
        return palette[key]