import base64
import os
from datetime import date, datetime
from functools import lru_cache
from html import escape
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from misc.misc import RESIZED_LOGOS_PATH
from streamlit_interface.color_palette import get_palette
from streamlit_interface.streamlit_utils import french_flag
from streamlit_interface.classement_TTFL_utils import accentuate_pct

# Assumed to already exist in your module (unchanged):
#   get_palette, french_flag, accentuate_pct, RESIZED_LOGOS_PATH


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
PLOT_FIELDS = (('d', 'graph_dates'), ('o', 'graph_opps'), ('t', 'graph_TTFLs'),
               ('w', 'graph_wins'), ('h', 'graph_ishome'))


def _s(v):
    """Cell -> clean string ('' for None/NaN, join lists)."""
    if v is None:
        return ''
    if isinstance(v, (list, tuple)):
        return ','.join(map(str, v))
    try:
        if v != v:  # NaN
            return ''
    except Exception:
        pass
    return str(v)


def _fmt_req(requested_date):
    if requested_date is None:
        requested_date = datetime.now()
    if isinstance(requested_date, (datetime, date)):
        return requested_date.strftime('%d/%m/%Y')
    return str(requested_date)


@lru_cache(maxsize=None)
def _logo_symbol(opp):
    """One <symbol> per team, read from disk once per process."""
    path = os.path.join(RESIZED_LOGOS_PATH, f'{opp}.png')
    try:
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        inner = f'<image href="data:image/png;base64,{b64}" width="100" height="100"/>'
    except OSError:
        inner = (f'<circle cx="50" cy="50" r="45" fill="#888"/>'
                 f'<text x="50" y="60" text-anchor="middle" font-size="30" fill="#fff">{escape(opp)}</text>')
    return f'<symbol id="logo-{escape(opp, quote=True)}" viewBox="0 0 100 100">{inner}</symbol>'


def build_logo_sprite(df):
    """Sprite with only the logos actually used by this dataframe, each embedded once."""
    opps = set()
    if 'graph_opps' in df.columns:
        for v in df['graph_opps']:
            opps.update(o for o in _s(v).split(',') if o)
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            + ''.join(_logo_symbol(o) for o in sorted(opps)) + '</svg>')


# ----------------------------------------------------------------------------
# Client-side script: draws the SVG plot on hover + one shared floating tooltip.
# NOT passed through the newline stripping (it contains // comments).
# ----------------------------------------------------------------------------
TOOLTIP_JS = r"""
<script>
const W = 600, H = 400, ML = 55, MR = 45, MT = 30, MB = 55, DAY = 86400000;
const MONTHS = ["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."];

const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const parseDate = s => { const [d, m, y] = s.split('/').map(Number); return new Date(y, m - 1, d); };
const fmt = d => String(d.getDate()).padStart(2, '0') + ' ' + MONTHS[d.getMonth()];

function yTicks(lo, hi, n = 6) {
  const raw = (hi - lo) / n;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map(m => m * mag).find(s => s >= raw);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

function plotSvg(ds) {
  const head = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="12">`;
  if (!ds.d) {
    return head + `<text x="${W/2}" y="${H/2}" text-anchor="middle" font-size="20">Pas de données disponibles</text></svg>`;
  }
  const dates = ds.d.split(',').map(parseDate);
  const req   = parseDate(ds.req);
  const opps  = ds.o.split(',');
  const ttfls = ds.t.split(',').map(Number);
  const wins  = ds.w.split(',').map(x => Math.round(+x));
  const home  = ds.h.split(',').map(x => Math.round(+x));
  const avg   = ds.avg === '' ? null : parseFloat(ds.avg);

  const njours = Math.round((req - dates[0]) / DAY);
  const span = Math.max(njours, 1);
  const xticklabelrot = njours < 40 ? -30 - njours * 3 / 4 : -30;

  let ymin = Math.min(0, Math.min(...ttfls) * 1.2);
  let ymax = Math.max(...ttfls) * 1.1;
  if (ymin === 0) ymin = -2;
  if (ymax === 0) ymax = 2;
  if (ymin === ymax) { ymin -= 1; ymax += 1; }

  const pw = W - ML - MR, ph = H - MT - MB, pad = 15;
  const X = d => ML + pad + ((d - dates[0]) / DAY) / span * (pw - 2 * pad);
  const Y = v => MT + (ymax - v) / (ymax - ymin) * ph;
  const o = [head];

  for (const t of yTicks(ymin, ymax)) {
    const y = Y(t).toFixed(1);
    o.push(`<line x1="${ML}" x2="${W-MR}" y1="${y}" y2="${y}" stroke="#999" stroke-opacity=".3"/>`);
    o.push(`<text x="${ML-6}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${t}</text>`);
  }
  dates.forEach((d, i) => {
    const x = X(d).toFixed(1), c = wins[i] ? '#2a9d3f' : '#d33';
    // The vlines ?
    o.push(`<line x1="${x}" x2="${x}" y1="${MT}" y2="${MT+ph}" stroke="${c}" stroke-opacity=".4" stroke-dasharray="4 3"/>`);
    // H/A at the top of the vlines
    o.push(`<text x="${x}" y="${MT}" text-anchor="middle" fill="${c}" font-weight="bold" font-size="11">${home[i] ? 'H' : 'A'}</text>`);
  });
  const xr = X(req).toFixed(1);
  o.push(`<line x1="${xr}" x2="${xr}" y1="${MT}" y2="${MT+ph}" stroke="#888" stroke-dasharray="4 3"/>`);
  if (avg !== null && !isNaN(avg)) {
    const ya = Y(avg).toFixed(1);
    o.push(`<line x1="${ML}" x2="${W-MR}" y1="${ya}" y2="${ya}" stroke="red" stroke-opacity=".4" stroke-dasharray="4 3"/>`);
  }
  const pts = dates.map((d, i) => `${X(d).toFixed(1)},${Y(ttfls[i]).toFixed(1)}`).join(' ');
  o.push(`<polyline points="${pts}" fill="none" stroke="#888" stroke-opacity=".7" stroke-width="1.5" stroke-dasharray="5 4"/>`);

  const size = njours < 173 ? Math.max(24, 46 - njours * 0.16) : 32;
  dates.forEach((d, i) => {
    o.push(`<use href="#logo-${esc(opps[i])}" x="${(X(d) - size/2).toFixed(1)}" y="${(Y(ttfls[i]) - size/2).toFixed(1)}" width="${size.toFixed(0)}" height="${size.toFixed(0)}"/>`);
  });
  
  // XTICKLABELS : compute number of ticks and then draw them
  const ticks = njours < 40
    ? [...dates, req]
    : Array.from({length: 6}, (_, i) => new Date(dates[0].getTime() + (req - dates[0]) * i / 5));
  for (const d of ticks) {
    o.push(`<text transform="translate(${X(d).toFixed(1)},${MT+ph+45}) rotate(${xticklabelrot})" font-size="15">${fmt(d)}</text>`);
  }
  // Title -> name of the player
  o.push(`<text x="${W/2}" y="14" text-anchor="middle" font-size="17" font-weight="bold">${esc(ds.name)}</text>`);
  // ylabel -> TTFL
  o.push(`<text x="2" y="${MT + ph/2}" font-size="12">TTFL</text>`);
  o.push('</svg>');
  return o.join('');
}

// One floating tooltip for everything (plots, cell tooltips, header tooltips).
// position:fixed so it is never clipped by the iframe/table the way
// the old absolutely-positioned CSS tooltips would be.
const tip = document.getElementById('tip');
let current = null;

function show(t) {
  if (t.dataset.req !== undefined) {           // plot tooltip: draw now
    tip.className = 'plot';
    tip.innerHTML = plotSvg(t.dataset);
  } else {                                     // text tooltip: reuse hidden span
    const src = t.querySelector('.tooltiptext');
    if (!src) return false;
    tip.className = '';
    tip.innerHTML = src.innerHTML;
  }
  tip.style.display = 'block';
  const r = t.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
  const band = visibleBand();

  let left = r.left + r.width / 2 - w / 2;
  left = Math.max(4, Math.min(left, window.innerWidth - w - 4));

  // Prefer above the cell; use below if that side has more room in the VISIBLE area.
  const roomAbove = r.top - band.top, roomBelow = band.bottom - r.bottom;
  let top = (roomAbove >= h + 8 || roomAbove >= roomBelow) ? r.top - h - 8 : r.bottom + 8;
  top = Math.min(top, band.bottom - h - 8);    // never run past the bottom of the screen
  top = Math.max(top, band.top + 8);           // never run past the top of the screen
  tip.style.left = left + 'px';
  tip.style.top = top + 'px';
  return true;
}

// The iframe can be much taller than the screen (e.g. height = whole table), so
// window.innerHeight is NOT what the user sees. Compute the visible slice of the
// iframe from the parent page. Falls back to the iframe itself if that is blocked.
const HEADER_OFFSET = 60;   // px of Streamlit's sticky top bar covering the page; set 0 to ignore
function visibleBand() {
  try {
    const fr = window.frameElement.getBoundingClientRect();
    const parentH = window.parent.innerHeight;
    return {
      top: Math.max(0, HEADER_OFFSET - fr.top),
      bottom: Math.min(window.innerHeight, parentH - fr.top)
    };
  } catch (e) {
    return {top: 0, bottom: window.innerHeight};
  }
}

document.addEventListener('mouseover', e => {
  const t = e.target.closest('.tooltip');
  if (!t || t === current) return;
  current = show(t) ? t : null;
});
document.addEventListener('mouseout', e => {
  const t = e.target.closest('.tooltip');
  if (t && !t.contains(e.relatedTarget)) { current = null; tip.style.display = 'none'; }
});
</script>
"""


# ----------------------------------------------------------------------------
# Main function
# ----------------------------------------------------------------------------
def df_to_html2(
    df,
    show_cols=['Joueur', 'Lieu', 'Équipe', 'Adversaire', 'TTFL', 'Statut'],
    tooltips={
            'Statut' : 'details',
            'Équipe' : 'team_info',
            'Adversaire' : 'opp_info',
            'TTFL' : 'allrel'
            },
    col_header_tooltips = {'Joueur' : 'Survoler pour voir le graphe d\'évolution des scores TTFL',
                          'TTFL' : 'Toutes les équipes contre : scores TTFL relatifs des équipes adverses contre cette équipe' + \
                          '<br>Postes contre : scores TTFL relatifs des joueurs de ce poste contre cette équipe',
                          'Adversaire' : 'Score TTFL relatif des joueurs de ce poste contre l\'équipe du joueur blessé, pendant ses absences.',
                          'Équipe' : 'Score TTFL relatif du joueur quand ce coéquipier est blessé (N : nombre de matchs où le joueur a joué avec ce coéquipier blessé)',
                          'Statut' : 'Survoler pour voir les détails de la blessure'},
    plot_tooltips=('Joueur',),          # was image_tooltips={'Joueur': 'plots'}; no 'plots' column anymore
    requested_date=None,                # 'dd/mm/YYYY', date or datetime; defaults to today
    avg_col='TTFL',                     # column whose first 4 chars give the red average line
    show_index=True,
    zebra_stripes=True,
    hover_highlight=True,
    bold_headers=True,
    padding=10,
    center_table=True,
    color_tooltip_pct=True,
    highlight_index=None,
    col_header_labels={'TTFL' : '<span style="text-decoration:overline">TTFL</span>'},
    highlight_frenchies=True,
    best_pick_allowed=False
):
    """Render a dark-mode HTML table. Plots are drawn client-side on hover.

    The returned string contains a <script>, so display it with
    streamlit.components.v1.html(...), not st.markdown(..., unsafe_allow_html=True).
    """

    palette = get_palette('table')

    hover_color = palette['hover']
    text_color = palette['text']
    header_text_color = palette['header_text']
    header_bkg_color = palette['header_bkg']
    zebra_even_color, zebra_odd_color = palette['even'], palette['odd']
    highlight_color = palette['pick']
    hover_highlight_color = palette['pick_hover']
    best_pick_color = palette['best_pick'] if best_pick_allowed else highlight_color
    hover_best_pick_color = palette['best_pick_hover'] if best_pick_allowed else hover_highlight_color
    tooltip_bkg_color = palette['tooltip_bkg']
    tooltip_text_color = palette['tooltip_text']
    injured_warning_color = palette['injured']
    injured_warning_color_hover = palette['injured_hover']

    css = f"""
    <style>
    body {{
        margin: 0;
        font-family: "Source Sans Pro", sans-serif;
    }}
    .custom-table-dark {{
        border-collapse: collapse;
        text-align: center;
        width: 100%;
        margin: {'0 auto' if center_table else '0'};
    }}
    .custom-table-dark th {{
        
        {'background-color: ' + header_bkg_color + ';' if bold_headers else ''}
        color: {header_text_color} !important;
        padding: {padding}px;
        text-align: center;
        border: none;
    }}
    .custom-table-dark th .header-text {{
        font-weight: bold;
    }}
    .custom-table-dark td {{
        padding: {padding}px;
        text-align: center;
        color: {text_color} !important;
        border: none;
        position: relative;
    }}
    {" .custom-table-dark tr:nth-child(even) { background-color: " + zebra_even_color + "; }" if zebra_stripes else ""}
    {" .custom-table-dark tr:nth-child(odd)  { background-color: " + zebra_odd_color + "; }" if zebra_stripes else ""}
    {(".custom-table-dark tr:hover { background-color: " + hover_color + " !important; }") if hover_highlight else ""}

    /* Tooltip triggers. The .tooltiptext spans are just hidden data holders now;
       the JS copies them into the single floating #tip below. */
    .tooltip {{
        position: relative;
        display: inline-block;
        cursor: help;
    }}
    .tooltip .tooltiptext {{
        display: none;
    }}
    #tip {{
        display: none;
        position: fixed;
        z-index: 1000;
        pointer-events: none;
        width: max-content;
        max-width: 500px;
        background-color: {tooltip_bkg_color};
        color: {tooltip_text_color};
        text-align: center;
        font-weight: normal;
        font-size: 13px;
        border-radius: 6px;
        padding: 6px 10px;
        box-shadow: 0 0 5px rgba(0,0,0,0.4);
        white-space: normal;
    }}
    #tip.plot {{
        max-width: none;
        padding: 4px;
        background-color: {"#F0F0F0"};
        color: {"#2A2A2A"};
    }}
    #tip svg {{
        display: block;
        width: 450px;
        height: auto;
        fill: currentColor;   /* axis labels / title follow the tooltip text color */
    }}
    .custom-table-dark tr.best-pick-row {{
        background-color: {best_pick_color} !important;
    }}
    .custom-table-dark tr.best-pick-row:hover {{
        background-color: {hover_best_pick_color} !important;
    }}
    .custom-table-dark tr.highlight-row {{
        background-color: {highlight_color} !important;
    }}
    .custom-table-dark tr.highlight-row:hover {{
        background-color: {hover_highlight_color} !important;
    }}
    .custom-table-dark tr.injured-pick-row {{
        background-color: {injured_warning_color} !important;
    }}
    .custom-table-dark tr.injured-pick-row:hover {{
        background-color: {injured_warning_color_hover} !important;
    }}
    </style>
    """

    # Get indices of rows with max TTFL value
    if best_pick_allowed and 'TTFL' in df.columns:
        best_pick_indices = df.index[df['TTFL'] == df['TTFL'].max()].tolist()

    req = escape(_fmt_req(requested_date), quote=True)

    # Build HTML table
    html = css + build_logo_sprite(df) + '<table class="custom-table-dark">'
    html += "<thead><tr>"
    if show_index:
        html += "<th>Rang</th>"

    for col in show_cols:
        col_label = col
        if col in col_header_labels:
            col_label = col_header_labels[col]
        if col in col_header_tooltips:
            html += (
                '<th>'
                f'<div class="tooltip"><span class="header-text">{col_label}<sup>?</sup></span>'
                f'<span class="tooltiptext">{col_header_tooltips[col]}</span></div>'
                '</th>'
            )
        else:
            html += f'<th><span class="header-text">{col_label}</span></th>'

    html += "</tr></thead><tbody>"

    for i, row in enumerate(df.itertuples(index=False), start=1):
        if highlight_index is not None and i == highlight_index:
            if 'Statut' in show_cols and getattr(row, 'Statut') != '':
                row_class = "injured-pick-row"
            else:
                if best_pick_allowed and (i - 1) in best_pick_indices:
                    row_class = "best-pick-row"
                else:
                    row_class = "highlight-row"
            html += f'<tr class="{row_class}">'
        else:
            html += "<tr>"
        if show_index:
            html += f"<td>{i}</td>"
        for col in show_cols:
            cell_value = getattr(row, col)
            raw_value = cell_value          # keep the unflagged value for the chart title

            if highlight_frenchies:
                cell_value = french_flag(cell_value, html=True)

            if plot_tooltips and col in plot_tooltips:
                data = ''.join(
                    f' data-{k}="{escape(_s(getattr(row, c)), quote=True)}"' for k, c in PLOT_FIELDS
                )
                avg = escape(_s(getattr(row, avg_col))[:4], quote=True)
                name = escape(_s(raw_value).split(' (')[0], quote=True)
                html += (
                    f'<td><div class="tooltip"{data} data-avg="{avg}" '
                    f'data-name="{name}" data-req="{req}">{cell_value}</div></td>'
                )

            elif tooltips and col in tooltips:
                tooltip_value = getattr(row, tooltips[col])
                if 'all time' in tooltip_value:
                    cell_value = str(cell_value[:4]) + '*' + str(cell_value[4:])
                html += (
                    '<td><div class="tooltip">'
                    f"{cell_value}"
                    f'<span class="tooltiptext">{accentuate_pct(tooltip_value) if color_tooltip_pct else tooltip_value}</span>'
                    "</div></td>"
                )
            else:
                html += f"<td>{cell_value}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    html = html.replace("\n", "").replace("\r", "")   # only the markup, never the script
    html += '<div id="tip"></div>' + TOOLTIP_JS
    return html


# ----------------------------------------------------------------------------
# Usage in Streamlit
# ----------------------------------------------------------------------------
# import streamlit.components.v1 as components
#
# html = df_to_html(df, requested_date="22/11/2026")
# row_h = 2 * 10 + 22                      # 2 * padding + text height (tune to your design)
# components.html(html, height=60 + len(df) * row_h, scrolling=False)   # page scrolls, like before
# # or: components.html(html, height=700, scrolling=True)               # table scrolls inside a box