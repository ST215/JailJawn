// JailJawn front end. Loads census.csv, draws the crowd on a canvas with
// pretext doing the text layout, and builds the charts as inline SVG.
// No framework; the data is small and the page is read more than operated.

import { prepareWithSegments, layoutWithLines } from "./vendor/layout.js";

const CSV_URLS = [
  "https://raw.githubusercontent.com/ST215/JailJawn/master/census.csv",
  "./census.csv",
];

const FACILITIES = [
  { key: "cfcf", name: "Curran-Fromhold (CFCF)", color: "var(--s1)" },
  { key: "dc", name: "Detention Center (DC)", color: "var(--s2)" },
  { key: "dc_phsw", name: "DC Public Health Wing", color: "var(--s3)" },
  { key: "picc", name: "Industrial Correctional (PICC)", color: "var(--s4)" },
  { key: "rcf", name: "Riverside (RCF)", color: "var(--s5)" },
];

// One glyph per person. Shape carries identity; color repeats it.
const KINDS = [
  { id: "men", glyph: "i", label: "man in a facility", css: "--men" },
  { id: "women", glyph: "y", label: "woman in a facility", css: "--accent" },
  { id: "juv", glyph: "j", label: "juvenile in an adult facility", css: "--juv" },
  { id: "hosp", glyph: "+", label: "in a hospital open ward", css: "--hosp" },
  { id: "trip", glyph: "!", label: "on an emergency trip", css: "--trip" },
  { id: "out", glyph: "~", label: "on furlough or work release", css: "--trip" },
  { id: "away", glyph: "o", label: "held by another jurisdiction", css: "--away" },
];

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => n.toLocaleString("en-US");
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

function parseDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function longDate(iso) {
  const d = parseDate(iso);
  return `${DOW[d.getUTCDay()]}, ${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}
function shortDate(iso) {
  const d = parseDate(iso);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}
function monthYear(iso) {
  const d = parseDate(iso);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}
const daysBetween = (a, b) => Math.round((parseDate(b) - parseDate(a)) / 86400000);

// ---------------------------------------------------------------- data

async function loadCsv() {
  let lastError;
  for (const url of CSV_URLS) {
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error(`${res.status} from ${url}`);
      return parseCsv(await res.text());
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError;
}

function parseCsv(text) {
  const lines = text.trim().split("\n");
  const header = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row = {};
    header.forEach((h, i) => (row[h] = cells[i] ?? ""));
    return row;
  });
}

const n = (v) => (v === "" || v == null ? 0 : Number(v));

function dayModel(row) {
  const g = (k) => n(row[k]);
  const nif = (c) => g(`temporarily_not_in_facility.total.male_${c}`) + g(`temporarily_not_in_facility.total.female_${c}`);
  return {
    date: row.census_date,
    total: g("total_population.total.total"),
    males: g("total_population.total.males"),
    females: g("total_population.total.females"),
    men: g("in_facility.total.adult_males"),
    women: g("in_facility.total.adult_females"),
    juv: g("in_facility.total.juvenile_males") + g("in_facility.total.juvenile_females"),
    hosp: nif("open_ward"),
    trip: nif("emergency_trips"),
    out: nif("furlough") + nif("workers"),
    away: g("other_jurisdictions.total.total"),
    lehigh: g("other_jurisdictions.lehigh_county.total"),
    facilities: Object.fromEntries(FACILITIES.map((f) => [f.key, g(`facility_totals.${f.key}.total`)])),
    raw: row,
  };
}

// ---------------------------------------------------------------- the wall

const wall = {
  canvas: $("#wall"),
  ctx: null,
  font: "",
  size: 14,
  lineHeight: 18,
  width: 0,
  height: 0,
  dpr: 1,
  glyphWidth: new Map(),
  prepared: new Map(), // key: size|text -> prepared
  // per-glyph state
  count: 0,
  cap: 0,
  homeX: new Float32Array(0),
  homeY: new Float32Array(0),
  x: new Float32Array(0),
  y: new Float32Array(0),
  vx: new Float32Array(0),
  vy: new Float32Array(0),
  born: new Float32Array(0),
  kind: new Uint8Array(0),
  chars: [],
  colors: [],
  pointer: { x: -9999, y: -9999, active: false },
  raf: 0,
  t0: 0,
};

function ensureCapacity(nGlyphs) {
  if (nGlyphs <= wall.cap) return;
  const cap = Math.max(nGlyphs, Math.ceil(wall.cap * 1.5), 4096);
  const grow = (arr, Ctor) => {
    const next = new Ctor(cap);
    next.set(arr);
    return next;
  };
  wall.homeX = grow(wall.homeX, Float32Array);
  wall.homeY = grow(wall.homeY, Float32Array);
  wall.x = grow(wall.x, Float32Array);
  wall.y = grow(wall.y, Float32Array);
  wall.vx = grow(wall.vx, Float32Array);
  wall.vy = grow(wall.vy, Float32Array);
  wall.born = grow(wall.born, Float32Array);
  wall.kind = grow(wall.kind, Uint8Array);
  wall.cap = cap;
}

function crowdText(day) {
  // Order: inside first, then the people who are out, then those held elsewhere.
  const parts = [
    ["men", day.men],
    ["women", day.women],
    ["juv", day.juv],
    ["hosp", day.hosp],
    ["trip", day.trip],
    ["out", day.out],
    ["away", day.away],
  ];
  let text = "";
  const kinds = [];
  for (const [id, count] of parts) {
    const k = KINDS.findIndex((x) => x.id === id);
    text += KINDS[k].glyph.repeat(Math.max(0, count));
    for (let i = 0; i < count; i++) kinds.push(k);
  }
  return { text, kinds };
}

function preparedFor(text, size) {
  const key = size + "|" + text;
  let p = wall.prepared.get(key);
  if (!p) {
    p = prepareWithSegments(text, `600 ${size}px "Public Sans"`, { wordBreak: "break-word" });
    wall.prepared.set(key, p);
    if (wall.prepared.size > 600) wall.prepared.delete(wall.prepared.keys().next().value);
  }
  return p;
}

// Pick the largest glyph size whose wall fits the height budget.
function chooseSize(text, width, budget) {
  const sizes = [20, 18, 16, 15, 14, 13, 12, 11, 10, 9, 8];
  for (const s of sizes) {
    const lh = Math.round(s * 1.3);
    const { height } = layoutWithLines(preparedFor(text, s), width, lh);
    if (height <= budget) return { size: s, lineHeight: lh, height };
  }
  const s = 8;
  const lh = Math.round(s * 1.3);
  return { size: s, lineHeight: lh, height: layoutWithLines(preparedFor(text, s), width, lh).height };
}

function measureGlyph(ch) {
  let w = wall.glyphWidth.get(ch);
  if (w == null) {
    w = wall.ctx.measureText(ch).width;
    wall.glyphWidth.set(ch, w);
  }
  return w;
}

function layoutWall(day, { resize = false } = {}) {
  const frame = wall.canvas.parentElement;
  const width = Math.max(200, Math.floor(frame.clientWidth));
  const budget = Math.max(180, Math.min(window.innerHeight * 0.58, 620));
  const { text, kinds } = crowdText(day);

  if (resize || width !== wall.width || !wall.font) {
    const pick = chooseSize(text, width, budget);
    wall.size = pick.size;
    wall.lineHeight = pick.lineHeight;
    wall.font = `600 ${wall.size}px "Public Sans"`;
    wall.glyphWidth.clear();
  }
  const prepared = preparedFor(text, wall.size);
  const { lines, height } = layoutWithLines(prepared, width, wall.lineHeight);

  wall.width = width;
  wall.height = Math.ceil(height) + wall.lineHeight;
  wall.dpr = Math.min(devicePixelRatio || 1, 2);
  wall.canvas.width = Math.round(width * wall.dpr);
  wall.canvas.height = Math.round(wall.height * wall.dpr);
  wall.canvas.style.height = wall.height + "px";
  wall.ctx = wall.canvas.getContext("2d");
  wall.ctx.setTransform(wall.dpr, 0, 0, wall.dpr, 0, 0);
  wall.ctx.font = wall.font;
  wall.ctx.textBaseline = "alphabetic";

  const previous = wall.count;
  ensureCapacity(text.length);
  const now = performance.now();
  let i = 0;
  const baseline = wall.lineHeight * 0.85;
  for (let li = 0; li < lines.length; li++) {
    let x = 0;
    const y = baseline + li * wall.lineHeight;
    for (const ch of lines[li].text) {
      wall.homeX[i] = x;
      wall.homeY[i] = y;
      wall.chars[i] = ch;
      wall.kind[i] = kinds[i] ?? 0;
      if (i >= previous || resize) {
        wall.x[i] = x + (Math.random() - 0.5) * 6;
        wall.y[i] = y - 24 - Math.random() * 30;
        wall.vx[i] = 0;
        wall.vy[i] = 0;
        wall.born[i] = now + (resize ? (i / text.length) * 900 : Math.random() * 250);
      }
      x += measureGlyph(ch);
      i++;
    }
  }
  wall.count = i;
  if (reduceMotion) {
    for (let k = 0; k < wall.count; k++) {
      wall.x[k] = wall.homeX[k];
      wall.y[k] = wall.homeY[k];
      wall.born[k] = 0;
    }
    drawWall(now);
  } else if (!wall.raf) {
    wall.raf = requestAnimationFrame(tick);
  }
}

function tick(now) {
  wall.raf = 0;
  const settled = drawWall(now);
  if (!settled || wall.pointer.active) wall.raf = requestAnimationFrame(tick);
}

function drawWall(now) {
  const ctx = wall.ctx;
  ctx.clearRect(0, 0, wall.width, wall.height);
  ctx.font = wall.font;
  const px = wall.pointer.x;
  const py = wall.pointer.y;
  const radius = 70;
  const r2 = radius * radius;
  let moving = false;
  let currentKind = -1;
  for (let i = 0; i < wall.count; i++) {
    const age = now - wall.born[i];
    if (age < 0) {
      moving = true;
      continue;
    }
    // spring toward home
    let ax = (wall.homeX[i] - wall.x[i]) * 0.12;
    let ay = (wall.homeY[i] - wall.y[i]) * 0.12;
    if (wall.pointer.active) {
      const dx = wall.x[i] - px;
      const dy = wall.y[i] - py;
      const d2 = dx * dx + dy * dy;
      if (d2 < r2 && d2 > 0.01) {
        const d = Math.sqrt(d2);
        const push = ((radius - d) / radius) * 2.2;
        ax += (dx / d) * push;
        ay += (dy / d) * push;
      }
    }
    wall.vx[i] = (wall.vx[i] + ax) * 0.72;
    wall.vy[i] = (wall.vy[i] + ay) * 0.72;
    wall.x[i] += wall.vx[i];
    wall.y[i] += wall.vy[i];
    if (Math.abs(wall.vx[i]) + Math.abs(wall.vy[i]) > 0.02) moving = true;
    const alpha = Math.min(1, age / 320);
    if (alpha < 1) moving = true;
    if (wall.kind[i] !== currentKind) {
      currentKind = wall.kind[i];
      ctx.fillStyle = wall.colors[currentKind];
    }
    ctx.globalAlpha = alpha;
    ctx.fillText(wall.chars[i], wall.x[i], wall.y[i]);
  }
  ctx.globalAlpha = 1;
  return !moving;
}

function wirePointer() {
  const c = wall.canvas;
  const set = (e) => {
    const r = c.getBoundingClientRect();
    wall.pointer.x = e.clientX - r.left;
    wall.pointer.y = e.clientY - r.top;
    wall.pointer.active = true;
    if (!wall.raf && !reduceMotion) wall.raf = requestAnimationFrame(tick);
  };
  c.addEventListener("pointermove", set);
  c.addEventListener("pointerdown", set);
  c.addEventListener("pointerleave", () => {
    wall.pointer.active = false;
    if (!wall.raf && !reduceMotion) wall.raf = requestAnimationFrame(tick);
  });
}

function renderLegend(day) {
  const counts = { men: day.men, women: day.women, juv: day.juv, hosp: day.hosp, trip: day.trip, out: day.out, away: day.away };
  $("#legend").innerHTML = KINDS.map(
    (k) => `<span><b style="color:var(${k.css})">${k.glyph}</b>${k.label}<span class="n">${fmt(counts[k.id])}</span></span>`
  ).join("");
}

// ---------------------------------------------------------------- scrubber

function wireScrubber(days) {
  const input = $("#day");
  const play = $("#play");
  input.max = String(days.length - 1);
  input.value = input.max;
  let timer = 0;

  const show = (idx) => {
    const day = days[idx];
    $("#ro-date").textContent = longDate(day.date);
    $("#ro-total").textContent = fmt(day.total);
    renderLegend(day);
    layoutWall(day);
  };
  input.addEventListener("input", () => show(Number(input.value)));

  const stop = () => {
    clearInterval(timer);
    timer = 0;
    play.textContent = "Play";
  };
  play.addEventListener("click", () => {
    if (timer) return stop();
    let idx = Number(input.value);
    if (idx >= days.length - 1) idx = 0;
    play.textContent = "Pause";
    timer = setInterval(() => {
      idx++;
      if (idx >= days.length) return stop();
      input.value = String(idx);
      show(idx);
    }, reduceMotion ? 120 : 55);
  });
  show(days.length - 1);
  return show;
}

// ---------------------------------------------------------------- charts

const svgEsc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

function niceTicks(min, max, count = 5) {
  const span = max - min || 1;
  const rough = span / count;
  const pow = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= rough) ?? pow * 10;
  const start = Math.ceil(min / step) * step;
  const ticks = [];
  for (let v = start; v <= max + 1e-9; v += step) ticks.push(Math.round(v * 1000) / 1000);
  return ticks;
}

function monthTicks(days) {
  const out = [];
  let last = "";
  days.forEach((d, i) => {
    const ym = d.date.slice(0, 7);
    if (ym !== last) {
      last = ym;
      out.push({ i, label: monthYear(d.date), month: Number(ym.slice(5)) });
    }
  });
  return out;
}

function lineChart({ mount, tip, days, value, color, height = 300, annotate = true }) {
  const W = 960;
  const H = height;
  const pad = { l: 46, r: 68, t: 18, b: 30 };
  const vals = days.map(value);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const spread = hi - lo || 1;
  const yMin = lo - spread * 0.08;
  const yMax = hi + spread * 0.08;
  const x = (i) => pad.l + (i / Math.max(1, days.length - 1)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - yMin) / (yMax - yMin)) * (H - pad.t - pad.b);

  let path = "";
  days.forEach((d, i) => {
    const gap = i > 0 && daysBetween(days[i - 1].date, d.date) > 1;
    path += `${i === 0 || gap ? "M" : "L"}${x(i).toFixed(1)},${y(vals[i]).toFixed(1)}`;
  });
  const area = `M${x(0).toFixed(1)},${(H - pad.b).toFixed(1)}` + days.map((d, i) => `L${x(i).toFixed(1)},${y(vals[i]).toFixed(1)}`).join("") + `L${x(days.length - 1).toFixed(1)},${(H - pad.b).toFixed(1)}Z`;

  const yTicks = niceTicks(yMin, yMax, 4);
  const mt = monthTicks(days).filter((t) => days.length < 120 || t.month % 3 === 1);
  const iMax = vals.indexOf(hi);
  const iMin = vals.indexOf(lo);
  const last = days.length - 1;

  const labels = annotate
    ? [
        { i: iMax, v: hi, dy: -10, text: `${fmt(hi)} · ${shortDate(days[iMax].date)}` },
        { i: iMin, v: lo, dy: -10, text: `${fmt(lo)} · ${shortDate(days[iMin].date)}` },
      ]
    : [];

  mount.innerHTML = `
  <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    ${yTicks.map((t) => `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" stroke="var(--grid)" stroke-width="1"/>
      <text class="tick" x="${pad.l - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${fmt(t)}</text>`).join("")}
    ${mt.map((t) => `<text class="tick" x="${x(t.i).toFixed(1)}" y="${H - 8}" text-anchor="${t.i === 0 ? "start" : "middle"}">${t.label}</text>`).join("")}
    <path d="${area}" fill="${color}" opacity="0.1"/>
    <path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${x(last).toFixed(1)}" cy="${y(vals[last]).toFixed(1)}" r="4.5" fill="${color}" stroke="var(--surface)" stroke-width="2"/>
    <text class="lab strong" x="${(x(last) + 10).toFixed(1)}" y="${(y(vals[last]) + 4).toFixed(1)}">${fmt(vals[last])}</text>
    ${labels.map((l) => `<circle cx="${x(l.i).toFixed(1)}" cy="${y(l.v).toFixed(1)}" r="4" fill="${color}" stroke="var(--surface)" stroke-width="2"/>
      <text class="lab" x="${x(l.i).toFixed(1)}" y="${(y(l.v) + l.dy).toFixed(1)}" text-anchor="${l.i > days.length * 0.8 ? "end" : l.i < days.length * 0.1 ? "start" : "middle"}">${svgEsc(l.text)}</text>`).join("")}
    <line id="xh" x1="0" x2="0" y1="${pad.t}" y2="${H - pad.b}" stroke="var(--axis)" stroke-width="1" style="display:none"/>
    <circle id="xd" r="5" fill="${color}" stroke="var(--surface)" stroke-width="2" style="display:none"/>
    <rect x="${pad.l}" y="0" width="${W - pad.l - pad.r}" height="${H}" fill="transparent" style="cursor:crosshair"/>
  </svg>`;

  const svg = mount.querySelector("svg");
  const hover = svg.querySelector("rect");
  const xh = svg.querySelector("#xh");
  const xd = svg.querySelector("#xd");
  const move = (e) => {
    const r = svg.getBoundingClientRect();
    const fx = ((e.clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(last, Math.round(((fx - pad.l) / (W - pad.l - pad.r)) * last)));
    xh.setAttribute("x1", x(i));
    xh.setAttribute("x2", x(i));
    xh.style.display = "";
    xd.setAttribute("cx", x(i));
    xd.setAttribute("cy", y(vals[i]));
    xd.style.display = "";
    tip.innerHTML = `${longDate(days[i].date)}<br><b>${fmt(vals[i])}</b> people`;
    tip.style.display = "block";
    tip.style.left = `${(x(i) / W) * r.width}px`;
    tip.style.top = `${(y(vals[i]) / H) * r.height + 10}px`;
  };
  hover.addEventListener("pointermove", move);
  hover.addEventListener("pointerleave", () => {
    xh.style.display = "none";
    xd.style.display = "none";
    tip.style.display = "none";
  });
}

function sparkline(days, value, color) {
  const W = 300;
  const H = 90;
  const vals = days.map(value);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const yMin = lo - (hi - lo || 1) * 0.1;
  const yMax = hi + (hi - lo || 1) * 0.1;
  const x = (i) => 4 + (i / Math.max(1, days.length - 1)) * (W - 8);
  const y = (v) => 6 + (1 - (v - yMin) / (yMax - yMin)) * (H - 12);
  let path = "";
  days.forEach((d, i) => {
    const gap = i > 0 && daysBetween(days[i - 1].date, d.date) > 1;
    path += `${i === 0 || gap ? "M" : "L"}${x(i).toFixed(1)},${y(vals[i]).toFixed(1)}`;
  });
  const last = days.length - 1;
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    <path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${x(0).toFixed(1)}" cy="${y(vals[0]).toFixed(1)}" r="3.5" fill="${color}" stroke="var(--surface-2)" stroke-width="2"/>
    <circle cx="${x(last).toFixed(1)}" cy="${y(vals[last]).toFixed(1)}" r="3.5" fill="${color}" stroke="var(--surface-2)" stroke-width="2"/>
  </svg>`;
}

function facilityPanels(days) {
  $("#fac-legend").innerHTML = FACILITIES.map((f) => `<span><i style="background:${f.color}"></i>${f.name}</span>`).join("");
  $("#chart-fac").innerHTML = FACILITIES.map((f) => {
    const first = days[0].facilities[f.key];
    const lastV = days[days.length - 1].facilities[f.key];
    const pct = first ? Math.round(((lastV - first) / first) * 100) : 0;
    const sign = pct > 0 ? "+" : "";
    return `<div class="multiple">
      <div class="name"><i style="background:${f.color}"></i>${f.name}</div>
      <div class="delta"><b style="color:var(--ink)">${fmt(first)}</b> → <b style="color:var(--ink)">${fmt(lastV)}</b> &nbsp;${sign}${pct}%</div>
      ${sparkline(days, (d) => d.facilities[f.key], f.color)}
    </div>`;
  }).join("");
}

function dowChart(days, mount, tip) {
  const overall = days.reduce((s, d) => s + d.total, 0) / days.length;
  const byDow = DOW.map((name, k) => {
    const vals = days.filter((d) => parseDate(d.date).getUTCDay() === k).map((d) => d.total);
    const mean = vals.reduce((s, v) => s + v, 0) / vals.length;
    return { name, mean, delta: mean - overall, n: vals.length };
  });
  const order = [1, 2, 3, 4, 5, 6, 0].map((k) => byDow[k]);
  const W = 960;
  const H = 240;
  const pad = { l: 46, r: 16, t: 20, b: 30 };
  const maxAbs = Math.max(...order.map((d) => Math.abs(d.delta))) * 1.25;
  const y = (v) => pad.t + (1 - (v + maxAbs) / (2 * maxAbs)) * (H - pad.t - pad.b);
  const slot = (W - pad.l - pad.r) / 7;
  const bw = Math.min(24, slot * 0.5);
  const ticks = niceTicks(-maxAbs, maxAbs, 4);
  const hiI = order.reduce((b, d, i) => (d.delta > order[b].delta ? i : b), 0);
  const loI = order.reduce((b, d, i) => (d.delta < order[b].delta ? i : b), 0);
  mount.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    ${ticks.map((t) => `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" stroke="var(--grid)"/>
      <text class="tick" x="${pad.l - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${t > 0 ? "+" : ""}${fmt(Math.round(t))}</text>`).join("")}
    <line x1="${pad.l}" x2="${W - pad.r}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" stroke="var(--axis)"/>
    ${order.map((d, i) => {
      const cx = pad.l + slot * i + slot / 2;
      const top = Math.min(y(0), y(d.delta));
      const h = Math.abs(y(0) - y(d.delta));
      const up = d.delta >= 0;
      const r = 4;
      const rect = up
        ? `M${cx - bw / 2},${y(0)} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${bw - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z`
        : `M${cx - bw / 2},${y(0)} v${h - r} a${r},${r} 0 0 0 ${r},${r} h${bw - 2 * r} a${r},${r} 0 0 0 ${r},${-r} v${-(h - r)} z`;
      const label = i === hiI || i === loI ? `<text class="lab" x="${cx}" y="${up ? top - 8 : top + h + 16}" text-anchor="middle">${d.delta > 0 ? "+" : ""}${Math.round(d.delta)}</text>` : "";
      return `<path d="${rect}" fill="${up ? "var(--ink)" : "var(--ink-3)"}" data-i="${i}"/>${label}
        <text class="tick" x="${cx}" y="${H - 8}" text-anchor="middle">${d.name}</text>
        <rect x="${pad.l + slot * i}" y="0" width="${slot}" height="${H - pad.b}" fill="transparent" data-i="${i}"/>`;
    }).join("")}
  </svg>`;
  const svg = mount.querySelector("svg");
  svg.addEventListener("pointermove", (e) => {
    const i = e.target.dataset.i;
    if (i == null) return;
    const d = order[Number(i)];
    const r = svg.getBoundingClientRect();
    tip.innerHTML = `${d.name}s, ${d.n} days<br><b>${fmt(Math.round(d.mean))}</b> on average, ${d.delta > 0 ? "+" : ""}${Math.round(d.delta)} vs all days`;
    tip.style.display = "block";
    tip.style.left = `${((pad.l + slot * Number(i) + slot / 2) / W) * r.width}px`;
    tip.style.top = `${(pad.t / H) * r.height}px`;
  });
  svg.addEventListener("pointerleave", () => (tip.style.display = "none"));
  return { byDow, overall, order };
}

function tiles(days) {
  const mean = (k) => days.reduce((s, d) => s + d[k], 0) / days.length;
  const max = (k) => days.reduce((b, d) => (d[k] > b[k] ? d : b), days[0]);
  const items = [
    { k: "hosp", label: "In a hospital open ward", foot: "Most on one day" },
    { k: "trip", label: "Out on an emergency trip", foot: "Most on one day" },
    { k: "out", label: "On furlough or work release", foot: "Most on one day" },
    { k: "away", label: "Held by another jurisdiction", foot: "Most on one day" },
  ];
  $("#tiles").innerHTML = items.map((it) => {
    const m = max(it.k);
    return `<div class="tile"><div class="label">${it.label}</div>
      <div class="value">${mean(it.k) < 10 ? mean(it.k).toFixed(1) : fmt(Math.round(mean(it.k)))}<small>people a day</small></div>
      <div class="foot">${it.foot}: ${fmt(m[it.k])} on ${shortDate(m.date)}</div></div>`;
  }).join("");
}

function findings(days, dow) {
  const first = days[0];
  const last = days[days.length - 1];
  const pct = Math.round(((last.total - first.total) / first.total) * 100);
  const peak = days.reduce((b, d) => (d.total > b.total ? d : b), days[0]);
  const low = days.reduce((b, d) => (d.total < b.total ? d : b), days[0]);
  const lehighDays = days.filter((d) => d.lehigh > 0).length;
  const lehighConst = days.every((d) => d.lehigh === last.lehigh);
  const juvMax = days.reduce((b, d) => (d.juv > b.juv ? d : b), days[0]);
  const juvDays = days.filter((d) => d.juv > 0).length;
  const womenShare = (100 * days.reduce((s, d) => s + d.females, 0) / days.reduce((s, d) => s + d.total, 0)).toFixed(1);
  const rcf = FACILITIES.find((f) => f.key === "rcf");
  const rcfPct = Math.round(((last.facilities.rcf - first.facilities.rcf) / first.facilities.rcf) * 100);
  const cfcfShare = Math.round((100 * last.facilities.cfcf) / Object.values(last.facilities).reduce((s, v) => s + v, 0));
  const missing = daysBetween(first.date, last.date) + 1 - days.length;
  const swing = days.slice(1).map((d, i) => ({ d, delta: d.total - days[i].total, adj: daysBetween(days[i].date, d.date) === 1 })).filter((x) => x.adj).reduce((b, x) => (Math.abs(x.delta) > Math.abs(b.delta) ? x : b));
  const sun = dow.byDow[0];
  const wed = dow.byDow[3];

  const items = [
    { big: `<em>${pct > 0 ? "+" : ""}${pct}%</em>`, text: `From ${fmt(first.total)} people on ${shortDate(first.date)} to ${fmt(last.total)} on ${shortDate(last.date)}. The peak was ${fmt(peak.total)} on ${shortDate(peak.date)}; the low, ${fmt(low.total)} on ${shortDate(low.date)}.` },
    { big: `<em>${rcfPct > 0 ? "+" : ""}${rcfPct}%</em> at Riverside`, text: `${rcf.name} went from ${fmt(first.facilities.rcf)} to ${fmt(last.facilities.rcf)} people, the steepest change of any building. Curran-Fromhold alone now holds ${cfcfShare}% of everyone in a city facility.` },
    { big: `<em>${fmt(last.lehigh)}</em> in Lehigh County`, text: lehighConst ? `The same number, every one of the ${fmt(days.length)} days recorded. Whoever they are, they have been in Allentown's jail for the whole life of this dataset.` : `Held in Lehigh County on ${fmt(lehighDays)} of ${fmt(days.length)} days recorded.` },
    { big: `Up to <em>${fmt(juvMax.juv)}</em> juveniles`, text: `Juveniles were held in adult facilities on ${fmt(juvDays)} of ${fmt(days.length)} days, peaking at ${fmt(juvMax.juv)} on ${shortDate(juvMax.date)}.` },
    { big: `<em>${womenShare}%</em> women`, text: `Women are a small and steady share. On ${shortDate(last.date)} there were ${fmt(last.females)} women and ${fmt(last.males)} men.` },
    { big: `<em>${Math.round(sun.mean - wed.mean) > 0 ? "+" : ""}${Math.round(sun.mean - wed.mean)}</em> on Sundays`, text: `Sundays average ${fmt(Math.round(sun.mean))} people and Wednesdays ${fmt(Math.round(wed.mean))}. Weekend arrests wait for court.` },
    { big: `<em>${fmt(Math.abs(swing.delta))}</em> in one night`, text: `The biggest overnight change: ${swing.delta > 0 ? "up" : "down"} ${fmt(Math.abs(swing.delta))} people going into ${shortDate(swing.d.date)}.` },
    { big: `<em>${fmt(days.length)}</em> days recorded`, text: `${fmt(missing)} days in the span are missing, either not posted by the city or missed by the scraper. The gaps are visible as breaks in the trend line.` },
  ];
  $("#findings-grid").innerHTML = items.map((it) => `<div class="finding"><div class="big">${it.big}</div><p>${it.text}</p></div>`).join("");
}

function tableView(day) {
  const r = day.raw;
  const g = (k) => (r[k] === "" ? "–" : fmt(n(r[k])));
  const rows = (table, keys, names, cols) =>
    `<table><caption>${table}</caption><thead><tr><th></th>${cols.map((c) => `<th>${c[0]}</th>`).join("")}</tr></thead><tbody>${keys
      .map((k, i) => `<tr><td>${names[i]}</td>${cols.map((c) => `<td>${g(`${c[1]}.${k}.${c[2]}`)}</td>`).join("")}</tr>`)
      .join("")}</tbody></table>`;
  const facKeys = [...FACILITIES.map((f) => f.key), "rcf_asdcu", "rcf_asdmod3", "weekenders", "total"];
  const facNames = [...FACILITIES.map((f) => f.name), "RCF ASDCU", "RCF ASDMOD3", "Weekenders", "Total"];
  $("#table-summary").textContent = `The ${shortDate(day.date)} census as a table`;
  $("#table-inner").innerHTML =
    rows("In facility", facKeys, facNames, [["Adult men", "in_facility", "adult_males"], ["Adult women", "in_facility", "adult_females"], ["Juvenile boys", "in_facility", "juvenile_males"], ["Juvenile girls", "in_facility", "juvenile_females"]]) +
    rows("Temporarily not in facility", facKeys, facNames, [["Workers", "temporarily_not_in_facility", "male_workers"], ["Furlough", "temporarily_not_in_facility", "male_furlough"], ["Open ward (M)", "temporarily_not_in_facility", "male_open_ward"], ["Open ward (F)", "temporarily_not_in_facility", "female_open_ward"], ["Trips (M)", "temporarily_not_in_facility", "male_emergency_trips"], ["Trips (F)", "temporarily_not_in_facility", "female_emergency_trips"]]) +
    rows("Facility totals", facKeys, facNames, [["Men", "facility_totals", "males"], ["Women", "facility_totals", "females"], ["Total", "facility_totals", "total"]]) +
    rows("Held in other jurisdictions", ["state_doc", "juveniles", "delaware_county", "lehigh_county", "all_other", "total"], ["State DOC", "Juveniles", "Delaware County", "Lehigh County", "All other", "Total"], [["Men", "other_jurisdictions", "males"], ["Women", "other_jurisdictions", "females"], ["Total", "other_jurisdictions", "total"]]) +
    rows("Total population", ["pdp_facilities", "other_jurisdictions", "total"], ["In or out of a PDP facility", "Other jurisdictions", "Total"], [["Men", "total_population", "males"], ["Women", "total_population", "females"], ["Total", "total_population", "total"]]);
}

// ---------------------------------------------------------------- boot

async function main() {
  const status = $("#status");
  let rows;
  try {
    rows = await loadCsv();
  } catch (err) {
    $("#hero-h1").textContent = "The census could not be loaded.";
    status.textContent = `Could not fetch census.csv (${err.message}). Try again in a minute.`;
    return;
  }
  const days = rows.map(dayModel).filter((d) => d.total > 0);
  const last = days[days.length - 1];
  const first = days[0];

  $("#hero-h1").innerHTML = `<span class="count">${fmt(last.total)}</span> people were held by Philadelphia on ${shortDate(last.date)}.`;
  $("#hero-eyebrow").textContent = `Philadelphia Department of Prisons · daily census · ${fmt(days.length)} days since ${shortDate(first.date)}`;
  document.title = `JailJawn · ${fmt(last.total)} people`;

  wall.colors = KINDS.map((k) => css(k.css));
  try {
    await document.fonts.load('600 14px "Public Sans"');
  } catch {
    /* fall back to whatever the canvas has */
  }
  wirePointer();
  const show = wireScrubber(days);
  let resizeTimer = 0;
  addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => layoutWall(days[Number($("#day").value)], { resize: true }), 120);
  });
  if (reduceMotion) $("#wall-hint").textContent = "";

  const pct = Math.round(((last.total - first.total) / first.total) * 100);
  $("#trend-lede").textContent = `Since ${shortDate(first.date)} the count has moved from ${fmt(first.total)} to ${fmt(last.total)}, ${pct < 0 ? "down" : "up"} ${Math.abs(pct)}%. Hover the line for any day.`;
  lineChart({ mount: $("#chart-total"), tip: $("#tip-total"), days, value: (d) => d.total, color: css("--accent") });

  const rcfFirst = first.facilities.rcf;
  const rcfLast = last.facilities.rcf;
  const piccFirst = first.facilities.picc;
  const piccLast = last.facilities.picc;
  $("#fac-lede").textContent = `Riverside went from ${fmt(rcfFirst)} to ${fmt(rcfLast)} people while the Industrial Correctional Center barely moved, ${fmt(piccFirst)} to ${fmt(piccLast)}. Two more units, RCF ASDCU and ASDMOD3, have sat at zero for most of the record.`;
  facilityPanels(days);

  const dow = dowChart(days, $("#chart-dow"), $("#tip-dow"));
  const sun = dow.byDow[0];
  const wed = dow.byDow[3];
  $("#dow-lede").textContent = `Sundays average ${fmt(Math.round(sun.mean))} people; Wednesdays ${fmt(Math.round(wed.mean))}. The difference is about ${fmt(Math.round(sun.mean - wed.mean))} people, every week, like a tide.`;

  tiles(days);
  findings(days, dow);
  tableView(last);
  status.textContent = `Latest census: ${longDate(last.date)}. Data refreshes from the repository each time this page loads.`;
  show(days.length - 1);
}

main();
