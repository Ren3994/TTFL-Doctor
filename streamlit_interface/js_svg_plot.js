/* =============================================================================
 * js_svg_plot.js - tooltip engine + SVG plot drawing
 * =============================================================================
 * Runs inside a 0-height components.html iframe; the table itself lives in the
 * main page (rendered with st.markdown). The engine wires tooltips onto
 * window.parent.document, so the table keeps the page's fonts and layout.
 *
 * Just before this script, the component defines:  const PLOTS = {key: spec};
 * Table cells carry data-plot="<key>" (plots) or a hidden .tooltiptext span.
 * ========================================================================== */

/* ---- 1. STYLE - every color / width / font in one place ------------------ */
const STYLE = {
  fontFamily: 'sans-serif',
  fontSize: 9.5,            // y tick labels + "TTFL"   (old: 8pt on 720px fig)
  tickFontSize: 9.5,        // x tick labels            (old: 8pt)
  letterFontSize: 12,       // H/A letters              (old: 10pt)
  titleFontSize: 12,        // player name              (old: 10pt)
  emptyFontSize: 24,

  figBg: '#ffffff',         // seaborn-v0_8-dark figure facecolor
  axesBg: '#EAEAF2',        // seaborn-v0_8-dark axes facecolor
  text: '#262626',          // seaborn text.color (.15)

  gridColor: '#808080',     // 'grey'
  gridOpacity: 0.2,         // old: alpha - 0.5
  gridStrokeWidth: 1.8,     // old: 1.5pt @ 120dpi, scaled to this canvas

  winColor: '#008000',      // 'g'
  lossColor: '#FF0000',     // 'r'
  lettersOpacity: 0.4,      // old: alpha - 0.3
  nLetters: 10,             // old letter_vlines: 10 stacked letters

  reqColor: '#808080',
  reqOpacity: 0.7,
  dash: '8 6',
  lineWidth: 1.8,           // 1.5pt @ 120dpi scaled

  avgColor: '#FF0000',      // 'r'
  avgOpacity: 0.4,

  curveColor: '#808080',
  curveOpacity: 0.7,
};

/* ---- 2. SVG helpers ------------------------------------------------------ */
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const attrs = obj => Object.entries(obj).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');
const line = (x1, y1, x2, y2, a) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"${attrs(a)}/>`;
const text = (x, y, str, a = {}) =>
  `<text x="${x}" y="${y}"${attrs(a)}>${esc(str)}</text>`;

/* ---- 3. drawPlot(spec): replicate the old seaborn-v0_8-dark look --------- */
function drawPlot(spec) {
  const out = [];
  out.push(`<svg viewBox="0 0 ${spec.w} ${spec.h}" xmlns="http://www.w3.org/2000/svg"` +
           ` font-family="${STYLE.fontFamily}" font-size="${STYLE.fontSize}" fill="${STYLE.text}">`);
  out.push(`<rect x="0" y="0" width="${spec.w}" height="${spec.h}" fill="${STYLE.figBg}"/>`);

  if (spec.empty) {
    out.push(text(spec.w / 2, spec.h / 2, 'Pas de données disponibles',
                  { 'text-anchor': 'middle', 'font-size': STYLE.emptyFontSize }));
    out.push('</svg>');
    return out.join('');
  }

  const [left, top, right, bottom] = spec.area;

  // (a) axes background (lavender)
  out.push(`<rect x="${left}" y="${top}" width="${right - left}" height="${bottom - top}"` +
           ` fill="${STYLE.axesBg}"/>`);

  // (b) one column of 10 H/A letters per game, centered vertically (old letter_vlines)
  const gap = (bottom - top) * 0.092;                     // 19.7pt linespacing, scaled
  const y0 = (top + bottom) / 2 - gap * (STYLE.nLetters - 1) / 2;
  for (const [x, , win, home] of spec.games) {
    const color = win ? STYLE.winColor : STYLE.lossColor;
    const letter = home ? 'H' : 'A';
    for (let i = 0; i < STYLE.nLetters; i++) {
      out.push(text(x, y0 + i * gap, letter, {
        'text-anchor': 'middle', fill: color, 'font-size': STYLE.letterFontSize,
        'fill-opacity': STYLE.lettersOpacity,
      }));
    }
  }

  // (c) horizontal grid + y labels on BOTH sides (old secondary_yaxis)
  for (const [y, label] of spec.yTicks) {
    out.push(line(left, y, right, y, { stroke: STYLE.gridColor,
                 'stroke-opacity': STYLE.gridOpacity, 'stroke-width': STYLE.gridStrokeWidth }));
    out.push(text(left - 4, y + 3, label, { 'text-anchor': 'end' }));
    out.push(text(right + 4, y + 3, label, { 'text-anchor': 'start' }));
  }

  // (d) requested-date line: dashed; solid in long ranges (old double-draw)
  out.push(line(spec.reqX, top, spec.reqX, bottom, {
    stroke: STYLE.reqColor, 'stroke-opacity': STYLE.reqOpacity,
    'stroke-width': STYLE.lineWidth,
    ...(spec.solidReq ? {} : { 'stroke-dasharray': STYLE.dash }),
  }));

  // (e) average line: first game -> requested date only (not the full width)
  if (spec.avgY !== null) {
    out.push(line(spec.games[0][0], spec.avgY, spec.reqX, spec.avgY, {
      stroke: STYLE.avgColor, 'stroke-opacity': STYLE.avgOpacity,
      'stroke-width': STYLE.lineWidth, 'stroke-dasharray': '7 7',
    }));
  }

  // (f) the connecting dashed curve
  const points = spec.games.map(g => `${g[0]},${g[1]}`).join(' ');
  out.push(`<polyline points="${points}" fill="none" stroke="${STYLE.curveColor}"` +
           ` stroke-opacity="${STYLE.curveOpacity}" stroke-width="${STYLE.lineWidth}"` +
           ` stroke-dasharray="${STYLE.dash}"/>`);

  // (g) opponent logos (old OffsetImage zoom sizes)
  const half = spec.logo / 2;
  for (const [x, y, , , opp] of spec.games) {
    out.push(`<use href="#logo-${esc(opp)}" x="${x - half}" y="${y - half}"` +
             ` width="${spec.logo}" height="${spec.logo}"/>`);
  }

  // (h) x tick labels, anchored like matplotlib (center/top at the tick, rotated CCW)
  const rot = spec.rot ?? -60;
  for (const [x, label] of spec.xTicks) {
    out.push(text(0, 0, label, {
      transform: `translate(${x},${bottom + 7}) rotate(${rot}) translate(0,7)`,
      'text-anchor': 'middle', 'font-size': STYLE.tickFontSize,
    }));
  }

  // (i) title just above the axes + TTFL ylabel
  out.push(text((left + right) / 2, top - 9, spec.title,
                { 'text-anchor': 'middle', 'font-size': STYLE.titleFontSize }));
  out.push(text(6, (top + bottom) / 2, 'TTFL', { 'font-size': STYLE.tickFontSize }));

  out.push('</svg>');
  return out.join('');
}

/* ---- 4. Parent-document tooltip engine ----------------------------------- */
(function () {
  const P = window.parent;                       // the real Streamlit page
  const DOC = P.document;

  // merge this table's plots into the shared registry on the parent
  P.__TTFL_PLOTS = Object.assign(P.__TTFL_PLOTS || {}, PLOTS);
  const svgCache = (P.__TTFL_SVG ||= {});
  function getPlotSvg(key) {
    if (!(key in svgCache)) {
      const spec = P.__TTFL_PLOTS[key];
      svgCache[key] = spec ? drawPlot(spec) : null;
    }
    return svgCache[key];
  }

  // move the logo symbols into the PARENT document: <use href="#logo-X"> inside
  // the injected SVG can only reference symbols of its own document.
  let sprite = DOC.getElementById('ttfl-logos');
  if (!sprite) {
    sprite = DOC.createElement('div');
    sprite.id = 'ttfl-logos';
    sprite.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
    DOC.body.appendChild(sprite);
  }
  for (const sym of document.querySelectorAll('symbol[id^="logo-"]')) {
    if (!DOC.getElementById(sym.id)) sprite.appendChild(DOC.importNode(sym, true));
  }

  // tooltip div: reuse or create in the parent
  let tip = DOC.getElementById('tip');
  if (!tip) {
    tip = DOC.createElement('div');
    tip.id = 'tip';
    DOC.body.appendChild(tip);
  }

  const HEADER_OFFSET = 60;                      // Streamlit's sticky header

  function show(el) {
    if (el.dataset.plot !== undefined) {
      const svg = getPlotSvg(el.dataset.plot);
      if (!svg) return false;
      tip.className = 'plot';
      tip.innerHTML = svg;
    } else {
      const source = el.querySelector('.tooltiptext');
      if (!source) return false;
      tip.className = '';
      tip.innerHTML = source.innerHTML;
    }
    tip.style.display = 'block';

    const cell = el.getBoundingClientRect();     // parent-viewport coordinates
    const w = tip.offsetWidth, h = tip.offsetHeight;

    let left = cell.left + cell.width / 2 - w / 2;
    left = Math.max(8, Math.min(left, P.innerWidth - w - 8));

    const roomAbove = cell.top - HEADER_OFFSET;
    const roomBelow = P.innerHeight - cell.bottom;
    let top = (roomAbove >= h + 8 || roomAbove >= roomBelow)
      ? cell.top - h - 8 : cell.bottom + 8;
    top = Math.min(top, P.innerHeight - h - 8);
    top = Math.max(top, HEADER_OFFSET + 8);

    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
    return true;
  }

  // re-wire idempotently: if a previous engine (earlier rerun / other table)
  // attached handlers, remove them first.
  if (P.__TTFL_OVER) DOC.removeEventListener('mouseover', P.__TTFL_OVER);
  if (P.__TTFL_OUT) DOC.removeEventListener('mouseout', P.__TTFL_OUT);
  let current = null;
  P.__TTFL_OVER = e => {
    const el = e.target.closest('.tooltip');
    if (!el || el === current) return;
    current = show(el) ? el : null;
  };
  P.__TTFL_OUT = e => {
    const el = e.target.closest('.tooltip');
    if (el && !el.contains(e.relatedTarget)) { current = null; tip.style.display = 'none'; }
  };
  DOC.addEventListener('mouseover', P.__TTFL_OVER);
  DOC.addEventListener('mouseout', P.__TTFL_OUT);
})();

/* =============================================================================
 * 5. CLICKABLE CELLS - <a class="cell-link"> wraps cells that link to another
 *    page (e.g. a player name -> its stats page). The anchor is generated by
 *    df_to_html() (see its cell_links parameter).
 *
 *    Plain left-click navigates the app IN THIS TAB. Ctrl/Cmd/Shift-click and
 *    middle-click keep the browser default (open in a new tab), and so does
 *    anything that goes wrong below.
 *
 *    Why the detour through the parent document? This table runs inside a
 *    Streamlit component iframe, and Streamlit sandboxes those iframes WITHOUT
 *    'allow-top-navigation'. A plain <a target="_top">, or setting
 *    window.top.location from inside this frame, is silently blocked
 *    (SecurityError). An anchor created IN THE PARENT document belongs to the
 *    parent's (unsandboxed) browsing context, so its navigation is allowed.
 * ========================================================================== */
document.addEventListener('click', e => {
  const a = e.target.closest('a.cell-link');
  if (!a) return;
  // Modified clicks (Ctrl/Cmd/Shift/Alt): let the browser handle them. The
  // anchor's own target="_blank" makes them open a new tab.
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  e.preventDefault();
  try {
    const parentDoc = window.parent.document;
    const nav = parentDoc.createElement('a');
    nav.href = a.href;
    nav.target = '_top';
    nav.style.display = 'none';
    parentDoc.body.appendChild(nav);
    nav.click();
    nav.remove();
  } catch (err) {
    window.open(a.href);   // parent unreachable (embedded/cross-origin app): open a new tab
  }
});