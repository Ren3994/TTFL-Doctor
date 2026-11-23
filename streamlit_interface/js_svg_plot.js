/* =============================================================================
 * plots.js  -  hover tooltips for the table
 * =============================================================================
 *
 * WHAT THIS FILE DOES
 *   1. Draws ONE plot (as an SVG string) from a "spec" computed in Python.
 *   2. Manages ONE floating tooltip (<div id="tip">) shared by every tooltip in
 *      the table: plots, cell tooltips and header tooltips.
 *
 * WHAT THIS FILE DOES NOT DO
 *   No parsing, no scaling, no axis maths. Python (plots.py) already did that.
 *   Every number in a spec is a ready-to-use pixel position inside a
 *   W x H canvas (600 x 400 by default).
 *
 *   >> To change the LAYOUT (margins, number of ticks, logo size, y range):
 *        edit plots.py.
 *   >> To change the LOOK (colors, line widths, dashes, fonts):
 *        edit STYLE just below.
 *   >> To change WHAT IS DRAWN or in which order:
 *        edit drawPlot().
 *
 * THE DATA CONTRACT
 *   Just before this script, the page defines a global object:
 *
 *       const PLOTS = { "<key>": spec, ... };
 *
 *   A table cell that has a plot carries  data-plot="<key>".
 *   A spec looks like this (all positions are pixels, origin = top-left):
 *
 *       {
 *         w: 600, h: 400,                 // canvas size (SVG viewBox)
 *         title: "Luka Doncic",           // text at the top
 *         empty: true,                    // ONLY when there is no data; nothing else is present
 *         area:   [left, top, right, bottom],   // the plotting rectangle
 *         yTicks: [[y, "10"], ...],       // horizontal grid lines: pixel y + label
 *         xTicks: [[x, "05 nov."], ...],  // x-axis labels:         pixel x + label
 *         games:  [[x, y, win, home, opp], ...],// one per game: pixel x/y of the point,
 *                                               // win (1/0), home (1/0), opponent code
 *         reqX:   560.0,                  // pixel x of the requested date (grey dashed line)
 *         avgY:   210.5,                  // pixel y of the average line, or null for none
 *         logo:   36                      // logo size in pixels
 *       }
 */


/* =============================================================================
 * 1. STYLE - every color / width / font in one place
 * ========================================================================== */
const STYLE = {
  // Text
  fontFamily: 'sans-serif',
  fontSize: 12,           // y-axis labels, "TTFL" label
  tickFontSize: 11,       // x-axis labels and the H / A letters
  titleFontSize: 14,      // player name
  xTickRotation: -60,      // degrees; x labels are tilted so they don't overlap
  emptyMessage: 'Pas de données disponibles',
  emptyFontSize: 25,

  // Horizontal grid lines
  gridColor: '#999',
  gridOpacity: 0.6,
  gridStrokeWidth : 1,

  // One dashed vertical line per game, colored by result, with an H (home) / A (away) letter on top
  winColor: '#2a9d3f',
  lossColor: '#d33',
  gameLineOpacity: 0.6,
  gameLineDash: '4 3',    // "dash gap" lengths in px

  // The dashed vertical line at the requested date
  reqColor: '#888',
  reqDash: '4 3',

  // The horizontal average line
  avgColor: 'red',
  avgOpacity: 0.6,
  avgDash: '4 3',

  // The curve connecting the games
  curveColor: '#888',
  curveOpacity: 0.7,
  curveWidth: 1.5,
  curveDash: '5 4',
};


/* =============================================================================
 * 2. SVG HELPERS - tiny functions that build SVG markup as strings
 *    (we build one big string and assign it to innerHTML once: much faster than
 *    creating DOM nodes one by one)
 * ========================================================================== */

// Escape text so a player name like "A&B <x>" can't break the markup.
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// {stroke: 'red', 'stroke-width': 2}  ->  ' stroke="red" stroke-width="2"'
const attrs = obj => Object.entries(obj).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');

// <line> from (x1, y1) to (x2, y2); `a` = extra attributes (stroke, dasharray, ...)
const line = (x1, y1, x2, y2, a) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"${attrs(a)}/>`;

// <text> anchored at (x, y); `a` = extra attributes (text-anchor, fill, ...)
const text = (x, y, str, a = {}) =>
  `<text x="${x}" y="${y}"${attrs(a)}>${esc(str)}</text>`;


/* =============================================================================
 * 3. drawPlot(spec) - the actual drawing. Returns an SVG string.
 *    Things are drawn in order: later ones appear ON TOP of earlier ones.
 * ========================================================================== */
function drawPlot(spec) {
  const out = [];

  // Opening <svg> tag. viewBox makes it scale: it is drawn in a w x h coordinate
  // system and displayed at whatever CSS size the tooltip gives it (600px wide, see #tip svg).
  out.push(`<svg viewBox="0 0 ${spec.w} ${spec.h}" xmlns="http://www.w3.org/2000/svg"` +
           ` font-family="${STYLE.fontFamily}" font-size="${STYLE.fontSize}">`);

  // ---- Case: no data for this player -> just a message, then stop ----------------
  if (spec.empty) {
    out.push(text(spec.w / 2, spec.h / 2, STYLE.emptyMessage,
                  { 'text-anchor': 'middle', 'font-size': STYLE.emptyFontSize }));
    out.push('</svg>');
    return out.join('');
  }

  // Unpack the plotting rectangle: left/right are x positions, top/bottom are y positions.
  const [left, top, right, bottom] = spec.area;

  // ---- (a) Horizontal grid lines + y-axis labels -----------------------------------
  for (const [y, label] of spec.yTicks) {
    out.push(line(left, y, right, y,
                  { stroke: STYLE.gridColor, 'stroke-opacity': STYLE.gridOpacity, 
                    'stroke-width': STYLE.gridStrokeWidth }));
    // Label sits 6px left of the plot; the +4 centers the text vertically on the line.
    out.push(text(left - 6, y + 4, label, { 'text-anchor': 'end' }));
  }

  // ---- (b) One vertical dashed line per game + the H / A letter -----------------------
  for (const [x, , win, home] of spec.games) {         // (the empty slot skips y)
    const color = win ? STYLE.winColor : STYLE.lossColor;
    out.push(line(x, top, x, bottom, {
      stroke: color, 'stroke-opacity': STYLE.gameLineOpacity,
      'stroke-dasharray': STYLE.gameLineDash,
    }));
    // The letter is placed just above the plot area (top - 6).
    out.push(text(x, top - 6, home ? 'H' : 'A', {
      'text-anchor': 'middle', fill: color,
      'font-weight': 'bold', 'font-size': STYLE.tickFontSize,
    }));
  }

  // ---- (c) Vertical line at the requested date ---------------------------------------
  out.push(line(spec.reqX, top, spec.reqX, bottom,
                { stroke: STYLE.reqColor, 'stroke-dasharray': STYLE.reqDash }));

  // ---- (d) Horizontal average line (only if Python gave us an average) -----------------
  if (spec.avgY !== null) {
    out.push(line(left, spec.avgY, right, spec.avgY, {
      stroke: STYLE.avgColor, 'stroke-opacity': STYLE.avgOpacity,
      'stroke-dasharray': STYLE.avgDash,
    }));
  }

  // ---- (e) The curve connecting the games ------------------------------------------------
  // <polyline points="x1,y1 x2,y2 ..."> ; fill="none" so it isn't filled like a polygon.
  const points = spec.games.map(g => `${g[0]},${g[1]}`).join(' ');
  out.push(`<polyline points="${points}" fill="none" stroke="${STYLE.curveColor}"` +
           ` stroke-opacity="${STYLE.curveOpacity}" stroke-width="${STYLE.curveWidth}"` +
           ` stroke-dasharray="${STYLE.curveDash}"/>`);

  // ---- (f) Opponent logos, centered on each point -------------------------------------------
  // <use href="#logo-LAL"> instantiates the <symbol> defined once in the page's logo sprite.
  // x/y of <use> is its top-left corner, so we shift by half the size to center it.
  const half = spec.logo / 2;
  for (const [x, y, , , opp] of spec.games) {
    out.push(`<use href="#logo-${esc(opp)}" x="${x - half}" y="${y - half}"` +
             ` width="${spec.logo}" height="${spec.logo}"/>`);
  }

  // ---- (g) x-axis labels: moved under the plot, then rotated around their own anchor point
  for (const [x, label] of spec.xTicks) {
    out.push(text(0, 0, label, {
      // translate() puts the label 14px under the plot; rotate() then tilts it.
      transform: `translate(${x},${bottom + 35}) rotate(${STYLE.xTickRotation})`,
      'font-size': STYLE.tickFontSize,
    }));
  }

  // ---- (h) Title (top center) and the y-axis name (left, vertically centered) ---------------
  out.push(text(spec.w / 2, 18, spec.title,
                { 'text-anchor': 'middle', 'font-size': STYLE.titleFontSize }));
  out.push(text(14, (top + bottom) / 2, 'TTFL'));

  out.push('</svg>');
  return out.join('');
}

// Drawing a plot is cheap but not free, so remember the result per key
// (key = "player|date"). Hovering the same cell again is then instant.
const svgCache = {};
function getPlotSvg(key) {
  if (!(key in svgCache)) {
    svgCache[key] = PLOTS[key] ? drawPlot(PLOTS[key]) : null;
  }
  return svgCache[key];
}


/* =============================================================================
 * 4. FLOATING TOOLTIP - one element reused for everything
 *
 *    Why one shared, position:fixed element instead of a CSS tooltip per cell?
 *    The table lives in an iframe; absolutely positioned tooltips would be cut
 *    off at the iframe's edges. A fixed element we position ourselves never is.
 * ========================================================================== */
const tip = document.getElementById('tip');   // the <div id="tip"> next to this script
let current = null;                            // the .tooltip element currently hovered

// How many px at the top of the screen are covered by Streamlit's sticky header.
// Tooltips will stay below that line. Set to 0 to ignore.
const HEADER_OFFSET = 60;

/* The iframe is often much TALLER than the screen (e.g. as tall as the whole table),
 * so window.innerHeight is NOT what the user sees. This returns the vertical slice of
 * the iframe that is really visible, in iframe coordinates: {top, bottom}.
 * If the browser doesn't let us look at the parent page, we assume the whole iframe is visible. */
function visibleBand() {
  try {
    const frame = window.frameElement.getBoundingClientRect(); // iframe position on the real screen
    const screenH = window.parent.innerHeight;                 // real screen height
    return {
      top: Math.max(0, HEADER_OFFSET - frame.top),             // part hidden above the screen (+ header)
      bottom: Math.min(window.innerHeight, screenH - frame.top) // part hidden below the screen
    };
  } catch (e) {
    return { top: 0, bottom: window.innerHeight };
  }
}

// Fill the tooltip for element `el` and put it next to it. Returns false if there's nothing to show.
function show(el) {
  // ---- 1. Fill the tooltip content --------------------------------------------------
  if (el.dataset.plot !== undefined) {
    // Plot cell: <div class="tooltip" data-plot="key">  ->  draw the SVG now.
    const svg = getPlotSvg(el.dataset.plot);
    if (!svg) return false;
    tip.className = 'plot';            // 'plot' class = wider, different background (see CSS)
    tip.innerHTML = svg;
  } else {
    // Text tooltip: the content sits in a hidden <span class="tooltiptext"> inside the element.
    const source = el.querySelector('.tooltiptext');
    if (!source) return false;
    tip.className = '';
    tip.innerHTML = source.innerHTML;
  }
  tip.style.display = 'block';         // must be visible before we can measure it

  // ---- 2. Work out where to put it ----------------------------------------------------
  const cell = el.getBoundingClientRect();   // position of the hovered element
  const w = tip.offsetWidth, h = tip.offsetHeight;
  const band = visibleBand();

  // Horizontal: centered on the cell, but kept inside the iframe (4px margin).
  let left = cell.left + cell.width / 2 - w / 2;
  left = Math.max(4, Math.min(left, window.innerWidth - w - 4));

  // Vertical: above the cell if it fits (or if there's more room above than below), else below.
  const roomAbove = cell.top - band.top;
  const roomBelow = band.bottom - cell.bottom;
  let top = (roomAbove >= h + 8 || roomAbove >= roomBelow)
    ? cell.top - h - 8
    : cell.bottom + 8;

  // Finally clamp to the visible slice so it can never end up off-screen.
  top = Math.min(top, band.bottom - h - 8);
  top = Math.max(top, band.top + 8);

  tip.style.left = left + 'px';
  tip.style.top = top + 'px';
  return true;
}

// ---- Event wiring -----------------------------------------------------------------------
// We listen on the whole document (event delegation) instead of on every cell:
// one listener, however many rows the table has.

// Mouse enters something inside a .tooltip -> show its tooltip.
document.addEventListener('mouseover', e => {
  const el = e.target.closest('.tooltip');
  if (!el || el === current) return;           // not a tooltip, or already showing it
  current = show(el) ? el : null;
});

// Mouse leaves the .tooltip (not just moves between its children) -> hide.
document.addEventListener('mouseout', e => {
  const el = e.target.closest('.tooltip');
  if (el && !el.contains(e.relatedTarget)) {
    current = null;
    tip.style.display = 'none';
  }
});