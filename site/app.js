// JailJawn front end. Loads the daily census (census.csv) and the 2013-2017
// record (legacy/summary.csv), draws the crowd on a canvas with pretext doing
// the text layout, and builds the charts as inline SVG. No framework.

import { prepareWithSegments, layoutWithLines } from "./vendor/layout.js";

const RAW = "https://raw.githubusercontent.com/ST215/JailJawn/master/";
const SOURCES = {
  current: [RAW + "census.csv", "./census.csv"],
  legacy: [RAW + "legacy/summary.csv", "./legacy/summary.csv"],
};

// Every facility that has ever appeared, with its full name. Abbreviations
// only ever appear next to the name.
const FACILITIES = [
  { key: "cfcf", name: "Curran-Fromhold Correctional Facility", abbr: "CFCF", color: "var(--s1)", eras: "both" },
  { key: "dc", name: "Detention Center", abbr: "DC", color: "var(--s2)", eras: "both" },
  { key: "dc_phsw", name: "Detention Center Public Health Services Wing", abbr: "DC PHSW", color: "var(--s3)", eras: "both" },
  { key: "picc", name: "Philadelphia Industrial Correctional Center", abbr: "PICC", color: "var(--s4)", eras: "both" },
  { key: "rcf", name: "Riverside Correctional Facility", abbr: "RCF", color: "var(--s5)", eras: "both" },
  { key: "rcf_asdcu", name: "Riverside Alternative and Special Detention Central Unit", abbr: "RCF ASDCU", color: "var(--ink-2)", eras: "current" },
  { key: "rcf_asdmod3", name: "Riverside Alternative and Special Detention Modular Unit 3", abbr: "RCF ASDMOD3", color: "var(--juv)", eras: "current" },
  { key: "hoc", name: "House of Correction", abbr: "HOC", color: "var(--ink-2)", eras: "legacy" },
  { key: "cec", name: "Community Education Centers, contracted beds", abbr: "CEC", color: "var(--ink-2)", eras: "legacy" },
  { key: "asd_cambria", name: "Alternative and Special Detention, Cambria", abbr: "", color: "var(--ink-2)", eras: "legacy" },
  { key: "asd_cannery", name: "Alternative and Special Detention, Cannery", abbr: "", color: "var(--ink-2)", eras: "legacy" },
  { key: "asd_wrp", name: "Alternative and Special Detention, Work Release Program", abbr: "", color: "var(--ink-2)", eras: "legacy" },
  { key: "asd_asdcu", name: "Alternative and Special Detention Central Unit", abbr: "ASDCU", color: "var(--ink-2)", eras: "legacy" },
  { key: "asd_mod3", name: "Alternative and Special Detention Modular Unit 3", abbr: "", color: "var(--ink-2)", eras: "legacy" },
  { key: "weekenders", name: "Weekenders program", abbr: "", color: "var(--ink-2)", eras: "both" },
];
const facName = (f) => (f.abbr ? `${f.name} (${f.abbr})` : f.name);
const CURRENT_FACS = FACILITIES.filter((f) => f.eras === "both" && f.key !== "weekenders");

// One symbol per person. Material Symbols codepoints; the shape carries
// identity and the color repeats it.
const KINDS = [
  { id: "men", glyph: "", label: "man in a facility", css: "--men" },
  { id: "women", glyph: "", label: "woman in a facility", css: "--accent" },
  { id: "juv", glyph: "", label: "juvenile in an adult facility", css: "--juv" },
  { id: "hosp", glyph: "", label: "in a hospital open ward", css: "--hosp" },
  { id: "trip", glyph: "", label: "on an emergency trip", css: "--trip" },
  { id: "out", glyph: "", label: "on furlough or work release", css: "--trip" },
  { id: "away", glyph: "", label: "held by another jurisdiction", css: "--away" },
];
const ICON_FONT = '"Material Symbols Rounded"';
const PHILLY_POP = 1_603_797; // 2020 Census

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => Math.round(n).toLocaleString("en-US");
const pct = (a, b) => Math.round(((b - a) / a) * 100);
const signed = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + fmt(Math.abs(v));
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DOW = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const parseDate = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };
const dayNum = (iso) => Math.round(parseDate(iso) / 86400000);
const isoFromNum = (n) => new Date(n * 86400000).toISOString().slice(0, 10);
const longDate = (iso) => { const d = parseDate(iso); return `${DOW[d.getUTCDay()]}, ${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`; };
const shortDate = (iso) => { const d = parseDate(iso); return `${MONTHS[d.getUTCMonth()].slice(0, 3)} ${d.getUTCDate()}, ${d.getUTCFullYear()}`; };
const monthYear = (iso) => { const d = parseDate(iso); return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };
const daysBetween = (a, b) => dayNum(b) - dayNum(a);

// ---------------------------------------------------------------- data

async function fetchCsv(urls) {
  let lastError;
  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error(`${res.status} from ${url}`);
      return parseCsv(await res.text());
    } catch (err) { lastError = err; }
  }
  throw lastError;
}
// A small RFC 4180 parser: quoted fields may hold commas and doubled quotes.
function parseCsv(text) {
  const records = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false; }
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(field); records.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field !== "" || row.length) { row.push(field); records.push(row); }
  const header = records[0];
  return records.slice(1).filter((r) => r.length > 1).map((cells) => {
    const obj = {};
    header.forEach((h, i) => (obj[h] = cells[i] ?? ""));
    return obj;
  });
}
const n = (v) => (v === "" || v == null ? 0 : Number(v));

function currentDay(row) {
  const g = (k) => n(row[k]);
  const nif = (f, c) => g(`temporarily_not_in_facility.${f}.male_${c}`) + g(`temporarily_not_in_facility.${f}.female_${c}`);
  const facilities = {};
  for (const f of FACILITIES) {
    if (f.eras === "legacy") continue;
    facilities[f.key] = {
      total: g(`facility_totals.${f.key}.total`),
      males: g(`in_facility.${f.key}.adult_males`),
      females: g(`in_facility.${f.key}.adult_females`),
      juv: g(`in_facility.${f.key}.juvenile_males`) + g(`in_facility.${f.key}.juvenile_females`),
      hosp: nif(f.key, "open_ward"),
      trip: nif(f.key, "emergency_trips"),
      out: nif(f.key, "furlough") + nif(f.key, "workers"),
    };
  }
  return {
    date: row.census_date, era: "current",
    total: g("total_population.total.total"), males: g("total_population.total.males"), females: g("total_population.total.females"),
    men: g("in_facility.total.adult_males"), women: g("in_facility.total.adult_females"),
    juv: g("in_facility.total.juvenile_males") + g("in_facility.total.juvenile_females"),
    hosp: nif("total", "open_ward"), trip: nif("total", "emergency_trips"), out: nif("total", "furlough") + nif("total", "workers"),
    away: g("other_jurisdictions.total.total"), lehigh: g("other_jurisdictions.lehigh_county.total"),
    facilities, raw: row,
  };
}

function legacyDay(row) {
  const g = (k) => n(row[k]);
  const facilities = {};
  for (const f of FACILITIES) {
    if (!(f.key in row)) continue;
    facilities[f.key] = { total: g(f.key), males: g(`${f.key}_males`), females: g(`${f.key}_females`), juv: g(`${f.key}_juveniles`), hosp: 0, trip: 0, out: 0 };
  }
  const away = g("other_jurisdictions");
  const inMales = g("in_facility_males") || g("males");
  const inFemales = g("in_facility_females") || g("females");
  return {
    date: row.date, era: "legacy",
    total: g("total"), males: g("males"), females: g("females"),
    men: Math.max(0, inMales - g("open_ward") - g("emergency_trips") - g("workers") - g("furlough")), women: inFemales,
    juv: g("juveniles_in_facility"), hosp: g("open_ward"), trip: g("emergency_trips"), out: g("workers") + g("furlough"),
    away, lehigh: g("lehigh_county"), note: row.note, facilities, raw: row,
  };
}

// The crowd for a day, optionally narrowed to one facility.
function composition(day, facility) {
  if (!facility) return { men: day.men, women: day.women, juv: day.juv, hosp: day.hosp, trip: day.trip, out: day.out, away: day.away };
  const f = day.facilities[facility];
  if (!f) return { men: 0, women: 0, juv: 0, hosp: 0, trip: 0, out: 0, away: 0 };
  return { men: f.males, women: f.females, juv: f.juv, hosp: f.hosp, trip: f.trip, out: f.out, away: 0 };
}
const headcount = (day, facility) => (facility ? day.facilities[facility]?.total ?? 0 : day.total);

// ---------------------------------------------------------------- the crowd
// A still picture of the latest census: one symbol per person on wide
// screens, one per several on phones, laid out by pretext and drawn once.
// Nothing here animates; the timeline below animates numbers instead.

const wall = {
  canvas: $("#wall"), ctx: null, font: "", size: 12, lineHeight: 14, width: 0, height: 0, dpr: 1,
  prepared: new Map(), colors: [], ratio: 1, spotlight: false, comp: null, count: 0,
};
const JUV = KINDS.findIndex((k) => k.id === "juv");
const ZWSP = "\u200b";

function crowdText(comp, ratio) {
  let text = "";
  const kinds = [];
  KINDS.forEach((k, ki) => {
    const people = Math.max(0, comp[k.id] | 0);
    const count = ratio === 1 ? people : people > 0 ? Math.max(1, Math.round(people / ratio)) : 0;
    text += (k.glyph + ZWSP).repeat(count);
    for (let i = 0; i < count; i++) kinds.push(ki);
  });
  return { text, kinds };
}

function preparedFor(text, size) {
  const key = size + "|" + text.length + "|" + text;
  let p = wall.prepared.get(key);
  if (!p) {
    p = prepareWithSegments(text, `${size}px ${ICON_FONT}`, { wordBreak: "break-word" });
    wall.prepared.set(key, p);
    if (wall.prepared.size > 40) wall.prepared.delete(wall.prepared.keys().next().value);
  }
  return p;
}

// The largest symbol, and the smallest people-per-symbol ratio, at which
// this count fits the frame. Phones get fewer, bigger symbols.
function chooseScale(total, width) {
  const budget = Math.max(260, Math.min(window.innerHeight * 0.55, 520));
  const minSize = width < 700 ? 13 : 10;
  for (const ratio of [1, 2, 5, 10, 20, 50]) {
    const probe = (KINDS[0].glyph + ZWSP).repeat(Math.max(1, Math.ceil(total / ratio)));
    for (const size of [22, 20, 18, 16, 15, 14, 13, 12, 11, 10]) {
      if (size < minSize) break;
      const lh = Math.round(size * 1.15);
      const { height } = layoutWithLines(preparedFor(probe, size), width, lh);
      if (height <= budget) return { ratio, size, lineHeight: lh };
    }
  }
  return { ratio: 50, size: minSize, lineHeight: Math.round(minSize * 1.15) };
}

function drawCrowd(comp) {
  wall.comp = comp;
  const width = Math.max(200, Math.floor(wall.canvas.parentElement.clientWidth - 28));
  const total = KINDS.reduce((s, k) => s + Math.max(0, comp[k.id] | 0), 0);
  const scale = chooseScale(total, width);
  wall.ratio = scale.ratio; wall.size = scale.size; wall.lineHeight = scale.lineHeight;
  wall.font = `${wall.size}px ${ICON_FONT}`;
  const { text, kinds } = crowdText(comp, wall.ratio);
  const { lines, height } = layoutWithLines(preparedFor(text, wall.size), width, wall.lineHeight);

  wall.width = width;
  wall.height = Math.ceil(height) + 4;
  wall.dpr = Math.min(devicePixelRatio || 1, 3);
  wall.canvas.width = Math.round(width * wall.dpr);
  wall.canvas.height = Math.round(wall.height * wall.dpr);
  wall.canvas.style.height = wall.height + "px";
  // A wide-gamut canvas where the display supports it.
  const ctx = wall.ctx || (wall.ctx = wall.canvas.getContext("2d", { colorSpace: "display-p3" }) || wall.canvas.getContext("2d"));
  ctx.setTransform(wall.dpr, 0, 0, wall.dpr, 0, 0);
  ctx.clearRect(0, 0, width, wall.height);
  ctx.textBaseline = "alphabetic";
  ctx.font = wall.font;
  const glyphWidth = new Map();
  const measure = (ch) => { let w = glyphWidth.get(ch); if (w == null) { w = ctx.measureText(ch).width; glyphWidth.set(ch, w); } return w; };
  const baseline = wall.lineHeight * 0.85;
  const kids = [];
  let i = 0, currentKind = -1;
  for (let li = 0; li < lines.length; li++) {
    let x = 0;
    const y = baseline + li * wall.lineHeight;
    for (const ch of lines[li].text) {
      if (ch === ZWSP) continue;
      const kind = kinds[i] ?? 0;
      if (wall.spotlight && kind === JUV) kids.push(x, y, ch);
      else {
        if (kind !== currentKind) { currentKind = kind; ctx.fillStyle = wall.colors[kind]; }
        ctx.globalAlpha = wall.spotlight ? 0.14 : 1;
        ctx.fillText(ch, x, y);
      }
      x += measure(ch);
      i++;
    }
  }
  if (kids.length) {
    ctx.globalAlpha = 1;
    ctx.font = `${Math.round(wall.size * 2.2)}px ${ICON_FONT}`;
    ctx.fillStyle = wall.colors[JUV];
    ctx.shadowColor = wall.colors[JUV]; ctx.shadowBlur = wall.size;
    for (let k = 0; k < kids.length; k += 3) ctx.fillText(kids[k + 2], kids[k] - wall.size * 0.6, kids[k + 1] + wall.size * 0.5);
    ctx.shadowBlur = 0; ctx.font = wall.font;
  }
  ctx.globalAlpha = 1;
  wall.count = i;
  $("#frame-note").textContent = wall.ratio === 1
    ? `Each symbol is one person. ${fmt(total)} symbols.`
    : `Each symbol stands for ${wall.ratio} people on a screen this size: ${fmt(i)} symbols for ${fmt(total)} people.`;
  const sym = $("#hero-symbol");
  if (sym) sym.textContent = wall.ratio === 1 ? "Every symbol below is one person counted that day." : `Every symbol below stands for ${wall.ratio} people counted that day.`;
}

function renderLegend(comp) {
  $("#legend").innerHTML = KINDS.map((k) => `<span><span class="ms" style="color:var(${k.css})" aria-hidden="true">${k.glyph}</span>${k.label}<span class="n">${fmt(comp[k.id])}</span></span>`).join("");
}

// Numbers count up or down to their new value instead of jumping.
const tweens = new Map();
function tweenNumber(el, to, suffix = "") {
  const from = Number(String(el.dataset.value ?? "0").replace(/[^0-9.-]/g, "")) || 0;
  el.dataset.value = String(to);
  if (reduceMotion || from === to) { el.textContent = fmt(to) + suffix; return; }
  const t0 = performance.now(), dur = 550;
  cancelAnimationFrame(tweens.get(el));
  const step = (now) => {
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(from + (to - from) * e) + suffix;
    if (p < 1) tweens.set(el, requestAnimationFrame(step));
  };
  tweens.set(el, requestAnimationFrame(step));
}

// ---------------------------------------------------------------- timeline

const state = { days: [], idx: 0, facility: "", compareIdx: -1, speed: 1, playing: false, clock: 0, playRaf: 0, lastTs: 0 };

function nearestIdx(iso) {
  const target = dayNum(iso);
  let best = 0, bestD = Infinity;
  state.days.forEach((d, i) => { const dd = Math.abs(dayNum(d.date) - target); if (dd < bestD) { bestD = dd; best = i; } });
  return best;
}

function showDay(idx, { fromPlay = false } = {}) {
  state.idx = idx;
  const day = state.days[idx];
  const comp = composition(day, state.facility);
  const count = headcount(day, state.facility);
  const first = state.days[0];
  const firstCount = headcount(first, state.facility);
  const change = count - firstCount;
  $("#ro-date").textContent = longDate(day.date) + (day.era === "legacy" ? " · from the 2013–2017 record" : "");
  tweenNumber($("#ro-total"), count);
  $("#ro-change").innerHTML = idx === 0 ? "The earliest day on record." : `<b>${signed(change)}</b> since ${shortDate(first.date)}${firstCount ? ` (${signed(pct(firstCount, count))}%)` : ""}`;
  const cats = $("#ro-cats");
  if (!cats.children.length) cats.innerHTML = KINDS.map((k) => `<div class="cat"><span class="ms" style="color:var(${k.css})" aria-hidden="true">${k.glyph}</span><b data-cat="${k.id}">0</b><span>${k.label}</span></div>`).join("");
  KINDS.forEach((k) => tweenNumber(cats.querySelector(`[data-cat="${k.id}"]`), comp[k.id]));
  $("#day").value = String(idx);
  if (!fromPlay) { $("#pick-date").value = day.date; history.replaceState(null, "", "#" + day.date); }
  markCharts(day.date);
  renderCompare();
}

function showLatestCrowd() {
  const latest = state.days[state.days.length - 1];
  const comp = composition(latest, state.facility);
  const f = FACILITIES.find((x) => x.key === state.facility);
  $("#st-date").textContent = `Latest census, ${longDate(latest.date)}` + (f ? `, ${facName(f)}` : "");
  $("#st-total").textContent = fmt(headcount(latest, state.facility));
  renderLegend(comp);
  drawCrowd(comp);
}

function setFacility(key) {
  state.facility = key;
  const f = FACILITIES.find((x) => x.key === key);
  $("#long-title").textContent = f ? `People held at ${facName(f)}, 2013 to today` : "People held by the Philadelphia Department of Prisons, 2013 to today";
  $("#trend-title").textContent = f ? `${facName(f)}, every day since March 2025` : "Every day since March 2025";
  drawMainCharts();
  showLatestCrowd();
  showDay(state.idx);
}

function play() {
  const btn = $("#play");
  if (state.playing) { stopPlay(); return; }
  state.playing = true;
  btn.textContent = "Pause";
  if (state.idx >= state.days.length - 1) { state.idx = 0; }
  state.clock = dayNum(state.days[state.idx].date);
  state.lastTs = 0;
  showDay(state.idx, { fromPlay: true });
  state.playRaf = requestAnimationFrame(playTick);
}
function stopPlay() {
  state.playing = false;
  cancelAnimationFrame(state.playRaf);
  $("#play").textContent = state.idx >= state.days.length - 1 ? "Play from 2013 again" : "Play";
  $("#caption").hidden = true;
  history.replaceState(null, "", "#" + state.days[state.idx].date);
  $("#pick-date").value = state.days[state.idx].date;
}
function playTick(ts) {
  if (!state.playing) return;
  if (!state.lastTs) state.lastTs = ts;
  const dt = Math.min(0.1, (ts - state.lastTs) / 1000);
  state.lastTs = ts;
  state.clock += 30.44 * state.speed * dt; // one month per second at speed 1
  const days = state.days;
  let idx = state.idx;
  while (idx + 1 < days.length && dayNum(days[idx + 1].date) <= state.clock) idx++;
  // jump the eight-year gap instead of waiting through it
  if (idx + 1 < days.length && daysBetween(days[idx].date, days[idx + 1].date) > 365 && state.clock > dayNum(days[idx].date) + 20) {
    const cap = $("#caption");
    cap.innerHTML = `<b>No record from ${monthYear(days[idx].date)} to ${monthYear(days[idx + 1].date)}.</b> The first scraper stopped in 2017. The daily record begins in 2025.`;
    cap.hidden = false;
    setTimeout(() => (cap.hidden = true), 3000);
    idx++;
    state.clock = dayNum(days[idx].date);
  }
  if (idx !== state.idx) showDay(idx, { fromPlay: true });
  if (idx >= days.length - 1) { stopPlay(); return; }
  state.playRaf = requestAnimationFrame(playTick);
}

function renderCompare() {
  const box = $("#compare");
  if (state.compareIdx < 0) { box.classList.remove("on"); return; }
  const a0 = state.days[state.compareIdx], b0 = state.days[state.idx];
  const [a, b] = dayNum(a0.date) <= dayNum(b0.date) ? [a0, b0] : [b0, a0];
  const ca = composition(a, state.facility), cb = composition(b, state.facility);
  const ta = headcount(a, state.facility), tb = headcount(b, state.facility);
  const facs = FACILITIES.filter((f) => (a.facilities[f.key]?.total || b.facilities[f.key]?.total));
  const row = (label, va, vb) => `<tr><td>${label}</td><td>${fmt(va)}</td><td>${fmt(vb)}</td><td class="${vb - va < 0 ? "neg" : ""}">${signed(vb - va)}</td></tr>`;
  box.innerHTML = `<button class="btn close" type="button" id="compare-close">Clear</button>
    <h3>${shortDate(a.date)} compared with ${shortDate(b.date)}</h3>
    <p>Between those two days the count went from <b>${fmt(ta)}</b> to <b>${fmt(tb)}</b>, a change of <b>${signed(tb - ta)}</b>${ta ? ` (${signed(pct(ta, tb))}%)` : ""}.</p>
    <div class="tablewrap"><table><thead><tr><th>Who</th><th>${shortDate(a.date)}</th><th>${shortDate(b.date)}</th><th>Change</th></tr></thead><tbody>
      ${KINDS.map((k) => row(k.label[0].toUpperCase() + k.label.slice(1), ca[k.id], cb[k.id])).join("")}
    </tbody></table>
    ${state.facility ? "" : `<table><thead><tr><th>Facility</th><th>${shortDate(a.date)}</th><th>${shortDate(b.date)}</th><th>Change</th></tr></thead><tbody>
      ${facs.map((f) => row(facName(f), a.facilities[f.key]?.total || 0, b.facilities[f.key]?.total || 0)).join("")}
    </tbody></table>`}</div>`;
  box.classList.add("on");
  $("#compare-close").addEventListener("click", () => { state.compareIdx = -1; $("#pick-compare").value = ""; renderCompare(); });
}

function wireControls() {
  const days = state.days;
  const range = $("#day");
  range.max = String(days.length - 1);
  range.addEventListener("input", () => { if (state.playing) stopPlay(); showDay(Number(range.value)); });
  $("#play").addEventListener("click", play);
  document.querySelectorAll("[data-speed]").forEach((b) => b.addEventListener("click", () => {
    state.speed = Number(b.dataset.speed);
    document.querySelectorAll("[data-speed]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  }));
  const pick = $("#pick-date");
  pick.min = days[0].date; pick.max = days[days.length - 1].date;
  pick.addEventListener("change", () => { if (!pick.value) return; if (state.playing) stopPlay(); showDay(nearestIdx(pick.value)); });
  const cmp = $("#pick-compare");
  cmp.min = days[0].date; cmp.max = days[days.length - 1].date;
  cmp.addEventListener("change", () => { state.compareIdx = cmp.value ? nearestIdx(cmp.value) : -1; renderCompare(); });
  const spot = $("#spot-kids");
  spot.addEventListener("click", () => {
    wall.spotlight = !wall.spotlight;
    spot.setAttribute("aria-pressed", String(wall.spotlight));
    spot.textContent = wall.spotlight ? "Show everyone" : "Show the children";
    drawCrowd(wall.comp);
  });
  const sel = $("#pick-facility");
  for (const f of FACILITIES) {
    const o = document.createElement("option");
    o.value = f.key; o.textContent = facName(f) + (f.eras === "legacy" ? " · 2013–2017 only" : f.eras === "current" ? " · since 2025" : "");
    sel.appendChild(o);
  }
  sel.addEventListener("change", () => setFacility(sel.value));
  let lastWidth = innerWidth, t = 0;
  addEventListener("resize", () => {
    if (innerWidth === lastWidth) return; // mobile URL bar changes height only
    lastWidth = innerWidth;
    clearTimeout(t);
    t = setTimeout(() => drawCrowd(wall.comp), 150);
  });
}

// ---------------------------------------------------------------- charts

const svgEsc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
function niceTicks(min, max, count = 5) {
  const span = max - min || 1, rough = span / count, pow = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= rough) ?? pow * 10;
  const ticks = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Math.round(v * 1000) / 1000);
  return ticks;
}

const charts = {};

// Time is on a real date axis so the 2017-2025 gap is honest.
function lineChart({ id, days, value, color, height = 320, zero = false, eras = false, hoverPill }) {
  const mount = $("#chart-" + id), tip = $("#tip-" + id);
  const W = 960, H = height, pad = { l: 50, r: 76, t: 22, b: 30 };
  const vals = days.map(value);
  const t0 = dayNum(days[0].date), t1 = dayNum(days[days.length - 1].date);
  const lo = zero ? 0 : Math.min(...vals), hi = Math.max(...vals);
  const spread = hi - lo || 1, yMin = zero ? 0 : lo - spread * 0.08, yMax = hi + spread * 0.1;
  const x = (iso) => pad.l + ((dayNum(iso) - t0) / Math.max(1, t1 - t0)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - yMin) / (yMax - yMin)) * (H - pad.t - pad.b);
  let path = "";
  days.forEach((d, i) => { const gap = i > 0 && daysBetween(days[i - 1].date, d.date) > 45; path += `${i === 0 || gap ? "M" : "L"}${x(d.date).toFixed(1)},${y(vals[i]).toFixed(1)}`; });
  const yTicks = niceTicks(yMin, yMax, 4);
  const years = [];
  for (let yr = parseDate(days[0].date).getUTCFullYear(); yr <= parseDate(days[days.length - 1].date).getUTCFullYear(); yr++) years.push(yr);
  const spanDays = t1 - t0;
  const xTicks = spanDays > 900
    ? years.map((yr) => ({ iso: `${yr}-01-01`, label: String(yr) })).filter((t) => dayNum(t.iso) >= t0 && dayNum(t.iso) <= t1)
    : days.map((d) => d.date.slice(0, 7)).filter((v, i, a) => a.indexOf(v) === i).map((ym) => ({ iso: ym + "-01", label: `${MONTHS[Number(ym.slice(5)) - 1].slice(0, 3)} ${ym.slice(0, 4)}` })).filter((t, i, a) => a.length < 8 || i % 3 === 0);
  const iMax = vals.indexOf(hi), iMin = vals.indexOf(Math.min(...vals)), last = days.length - 1;
  const labels = [{ i: iMax, v: vals[iMax], dy: -10, text: `${fmt(vals[iMax])} · ${shortDate(days[iMax].date)}` }];
  if (iMin !== last) labels.push({ i: iMin, v: vals[iMin], dy: -10, text: `${fmt(vals[iMin])} · ${shortDate(days[iMin].date)}` });
  let eraMarks = "";
  if (eras) {
    const gapStart = days.findIndex((d, i) => i > 0 && daysBetween(days[i - 1].date, d.date) > 365);
    if (gapStart > 0) {
      const a = x(days[gapStart - 1].date), b = x(days[gapStart].date);
      eraMarks = `<rect x="${a.toFixed(1)}" y="${pad.t}" width="${(b - a).toFixed(1)}" height="${H - pad.t - pad.b}" fill="var(--surface-2)"/>
        <text class="era" x="${((a + b) / 2).toFixed(1)}" y="${(pad.t + 16)}" text-anchor="middle">no record</text>`;
    }
  }
  mount.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    ${eraMarks}
    ${yTicks.map((t) => `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" stroke="var(--grid)"/><text class="tick" x="${pad.l - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${fmt(t)}</text>`).join("")}
    ${xTicks.map((t) => `<text class="tick" x="${x(t.iso).toFixed(1)}" y="${H - 8}" text-anchor="middle">${t.label}</text>`).join("")}
    <path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    ${days.length < 200 ? days.map((d, i) => `<circle cx="${x(d.date).toFixed(1)}" cy="${y(vals[i]).toFixed(1)}" r="2.5" fill="${color}"/>`).join("") : ""}
    <circle cx="${x(days[last].date).toFixed(1)}" cy="${y(vals[last]).toFixed(1)}" r="4.5" fill="${color}" stroke="var(--surface)" stroke-width="2"/>
    <text class="lab strong" x="${(x(days[last].date) + 10).toFixed(1)}" y="${(y(vals[last]) + 4).toFixed(1)}">${fmt(vals[last])}</text>
    ${labels.map((l) => `<circle cx="${x(days[l.i].date).toFixed(1)}" cy="${y(l.v).toFixed(1)}" r="4" fill="${color}" stroke="var(--surface)" stroke-width="2"/><text class="lab" x="${x(days[l.i].date).toFixed(1)}" y="${(y(l.v) + l.dy).toFixed(1)}" text-anchor="${l.i > days.length * 0.8 ? "end" : l.i < days.length * 0.1 ? "start" : "middle"}">${svgEsc(l.text)}</text>`).join("")}
    <line class="mark" x1="0" x2="0" y1="${pad.t}" y2="${H - pad.b}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="3 3" style="display:none"/>
    <line class="xh" x1="0" x2="0" y1="${pad.t}" y2="${H - pad.b}" stroke="var(--axis)" style="display:none"/>
    <circle class="xd" r="5" fill="${color}" stroke="var(--surface)" stroke-width="2" style="display:none"/>
    <rect class="hit" x="${pad.l}" y="0" width="${W - pad.l - pad.r}" height="${H}" fill="transparent" style="cursor:crosshair"/>
  </svg>`;
  const svg = mount.querySelector("svg"), xh = svg.querySelector(".xh"), xd = svg.querySelector(".xd"), mark = svg.querySelector(".mark");
  const showAt = (i) => {
    const r = svg.getBoundingClientRect();
    xh.setAttribute("x1", x(days[i].date)); xh.setAttribute("x2", x(days[i].date)); xh.style.display = "";
    xd.setAttribute("cx", x(days[i].date)); xd.setAttribute("cy", y(vals[i])); xd.style.display = "";
    tip.innerHTML = `${longDate(days[i].date)}<br><b>${fmt(vals[i])}</b> ${id === "kids" ? (vals[i] === 1 ? "child" : "children") : "people"}`;
    tip.style.display = "block";
    tip.style.left = `${(x(days[i].date) / W) * r.width}px`;
    tip.style.top = `${(y(vals[i]) / H) * r.height - 8}px`;
  };
  const nearest = (clientX) => {
    const r = svg.getBoundingClientRect();
    const t = t0 + (((clientX - r.left) / r.width) * W - pad.l) / (W - pad.l - pad.r) * (t1 - t0);
    let best = 0, bd = Infinity;
    days.forEach((d, i) => { const dd = Math.abs(dayNum(d.date) - t); if (dd < bd) { bd = dd; best = i; } });
    return best;
  };
  svg.querySelector(".hit").addEventListener("pointermove", (e) => { showAt(nearest(e.clientX)); hoverPill?.classList.add("off"); });
  svg.querySelector(".hit").addEventListener("pointerdown", (e) => { const i = nearest(e.clientX); showAt(i); if (state.playing) stopPlay(); showDay(state.days.indexOf(days[i]) >= 0 ? state.days.indexOf(days[i]) : nearestIdx(days[i].date)); });
  svg.querySelector(".hit").addEventListener("pointerleave", () => { xh.style.display = "none"; xd.style.display = "none"; tip.style.display = "none"; });
  charts[id] = { days, mark, x };
}

function markCharts(iso) {
  for (const c of Object.values(charts)) {
    if (!c.mark) continue;
    const inRange = dayNum(iso) >= dayNum(c.days[0].date) && dayNum(iso) <= dayNum(c.days[c.days.length - 1].date);
    c.mark.style.display = inRange ? "" : "none";
    c.mark.setAttribute("x1", c.x(iso)); c.mark.setAttribute("x2", c.x(iso));
  }
}

function yearBars(days) {
  const mount = $("#chart-years"), tip = $("#tip-years");
  const byYear = new Map();
  days.forEach((d) => { const yr = d.date.slice(0, 4); const e = byYear.get(yr) || { sum: 0, n: 0 }; e.sum += headcount(d, state.facility); e.n++; byYear.set(yr, e); });
  const years = [...byYear.entries()].map(([yr, e]) => ({ yr, mean: e.sum / e.n, n: e.n })).sort((a, b) => a.yr.localeCompare(b.yr));
  const W = 960, H = 260, pad = { l: 50, r: 16, t: 26, b: 30 };
  const hi = Math.max(...years.map((y) => y.mean)) * 1.12;
  const y = (v) => pad.t + (1 - v / hi) * (H - pad.t - pad.b);
  const slot = (W - pad.l - pad.r) / years.length, bw = Math.min(24, slot * 0.55);
  mount.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    ${niceTicks(0, hi, 4).map((t) => `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" stroke="var(--grid)"/><text class="tick" x="${pad.l - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${fmt(t)}</text>`).join("")}
    <line x1="${pad.l}" x2="${W - pad.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--axis)"/>
    ${years.map((yv, i) => { const cx = pad.l + slot * i + slot / 2, top = y(yv.mean), h = y(0) - top, r = 4; const first = i === 0 || i === years.length - 1;
      return `<path d="M${cx - bw / 2},${y(0)} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${bw - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z" fill="${yv.n < 20 ? "var(--ink-3)" : "var(--accent)"}" data-i="${i}"/>
        ${first ? `<text class="lab" x="${cx}" y="${top - 8}" text-anchor="middle">${fmt(yv.mean)}</text>` : ""}
        <text class="tick" x="${cx}" y="${H - 8}" text-anchor="middle">${yv.yr}${yv.n < 20 ? "*" : ""}</text>
        <rect x="${pad.l + slot * i}" y="0" width="${slot}" height="${H - pad.b}" fill="transparent" data-i="${i}"/>`; }).join("")}
    <text class="tick" x="${W - pad.r}" y="${H - 8}" text-anchor="end">* fewer than 20 days recorded</text>
  </svg>`;
  const svg = mount.querySelector("svg");
  svg.addEventListener("pointermove", (e) => { const i = e.target.dataset.i; if (i == null) return; const yv = years[Number(i)]; const r = svg.getBoundingClientRect();
    tip.innerHTML = `${yv.yr}, ${yv.n} day${yv.n === 1 ? "" : "s"} recorded<br><b>${fmt(yv.mean)}</b> on average`; tip.style.display = "block";
    tip.style.left = `${((pad.l + slot * Number(i) + slot / 2) / W) * r.width}px`; tip.style.top = `${(pad.t / H) * r.height}px`; });
  svg.addEventListener("pointerleave", () => (tip.style.display = "none"));
}

function sparkline(days, value, color) {
  const W = 300, H = 90, vals = days.map(value), lo = Math.min(...vals), hi = Math.max(...vals);
  const yMin = lo - (hi - lo || 1) * 0.1, yMax = hi + (hi - lo || 1) * 0.1;
  const t0 = dayNum(days[0].date), t1 = dayNum(days[days.length - 1].date);
  const x = (iso) => 4 + ((dayNum(iso) - t0) / Math.max(1, t1 - t0)) * (W - 8), y = (v) => 6 + (1 - (v - yMin) / (yMax - yMin)) * (H - 12);
  let path = "";
  days.forEach((d, i) => { const gap = i > 0 && daysBetween(days[i - 1].date, d.date) > 45; path += `${i === 0 || gap ? "M" : "L"}${x(d.date).toFixed(1)},${y(vals[i]).toFixed(1)}`; });
  const last = days.length - 1;
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    <path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${x(days[0].date).toFixed(1)}" cy="${y(vals[0]).toFixed(1)}" r="3.5" fill="${color}" stroke="var(--surface-2)" stroke-width="2"/>
    <circle cx="${x(days[last].date).toFixed(1)}" cy="${y(vals[last]).toFixed(1)}" r="3.5" fill="${color}" stroke="var(--surface-2)" stroke-width="2"/></svg>`;
}

function facilityPanels(days) {
  const panel = (f, series) => {
    const first = series[0].facilities[f.key].total, lastV = series[series.length - 1].facilities[f.key].total;
    return `<div class="multiple"><div class="name"><i style="background:${f.color}"></i>${facName(f)}</div>
      <div class="delta"><b>${fmt(first)}</b> on ${shortDate(series[0].date)} → <b>${fmt(lastV)}</b> on ${shortDate(series[series.length - 1].date)}${first ? ` · ${signed(pct(first, lastV))}%` : ""}</div>
      ${sparkline(series, (d) => d.facilities[f.key].total, f.color)}</div>`;
  };
  $("#chart-fac").innerHTML = CURRENT_FACS.map((f) => panel(f, days.filter((d) => d.facilities[f.key]))).join("");
  const gone = FACILITIES.filter((f) => f.eras === "legacy");
  $("#chart-fac-gone").innerHTML = gone.map((f) => { const s = days.filter((d) => d.facilities[f.key] && d.facilities[f.key].total > 0); return s.length > 1 ? panel(f, s) : ""; }).join("");
}

function dowChart(days) {
  const mount = $("#chart-dow"), tip = $("#tip-dow");
  const overall = days.reduce((s, d) => s + headcount(d, state.facility), 0) / days.length;
  const byDow = DOW.map((name, k) => { const vals = days.filter((d) => parseDate(d.date).getUTCDay() === k).map((d) => headcount(d, state.facility)); const mean = vals.reduce((s, v) => s + v, 0) / (vals.length || 1); return { name, mean, delta: mean - overall, n: vals.length }; });
  const order = [1, 2, 3, 4, 5, 6, 0].map((k) => byDow[k]);
  const W = 960, H = 240, pad = { l: 50, r: 16, t: 20, b: 30 };
  const maxAbs = Math.max(1, Math.max(...order.map((d) => Math.abs(d.delta))) * 1.25);
  const y = (v) => pad.t + (1 - (v + maxAbs) / (2 * maxAbs)) * (H - pad.t - pad.b);
  const slot = (W - pad.l - pad.r) / 7, bw = Math.min(24, slot * 0.5);
  const hiI = order.reduce((b, d, i) => (d.delta > order[b].delta ? i : b), 0), loI = order.reduce((b, d, i) => (d.delta < order[b].delta ? i : b), 0);
  mount.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="aspect-ratio:${W}/${H}">
    ${niceTicks(-maxAbs, maxAbs, 4).map((t) => `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" stroke="var(--grid)"/><text class="tick" x="${pad.l - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${t > 0 ? "+" : ""}${fmt(t)}</text>`).join("")}
    <line x1="${pad.l}" x2="${W - pad.r}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" stroke="var(--axis)"/>
    ${order.map((d, i) => { const cx = pad.l + slot * i + slot / 2, top = Math.min(y(0), y(d.delta)), h = Math.abs(y(0) - y(d.delta)), up = d.delta >= 0, r = Math.min(4, h / 2);
      const rect = up ? `M${cx - bw / 2},${y(0)} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${bw - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z` : `M${cx - bw / 2},${y(0)} v${h - r} a${r},${r} 0 0 0 ${r},${r} h${bw - 2 * r} a${r},${r} 0 0 0 ${r},${-r} v${-(h - r)} z`;
      const label = i === hiI || i === loI ? `<text class="lab" x="${cx}" y="${up ? top - 8 : top + h + 16}" text-anchor="middle">${signed(d.delta)}</text>` : "";
      return `<path d="${rect}" fill="${up ? "var(--ink)" : "var(--ink-3)"}" data-i="${i}"/>${label}<text class="tick" x="${cx}" y="${H - 8}" text-anchor="middle">${d.name}</text><rect x="${pad.l + slot * i}" y="0" width="${slot}" height="${H - pad.b}" fill="transparent" data-i="${i}"/>`; }).join("")}</svg>`;
  const svg = mount.querySelector("svg");
  svg.addEventListener("pointermove", (e) => { const i = e.target.dataset.i; if (i == null) return; const d = order[Number(i)]; const r = svg.getBoundingClientRect();
    tip.innerHTML = `${d.name}s, ${d.n} days<br><b>${fmt(d.mean)}</b> on average, ${signed(d.delta)} against all days`; tip.style.display = "block";
    tip.style.left = `${((pad.l + slot * Number(i) + slot / 2) / W) * r.width}px`; tip.style.top = `${(pad.t / H) * r.height}px`; svg.closest(".chart-card").querySelector(".how")?.classList.add("off"); });
  svg.addEventListener("pointerleave", () => (tip.style.display = "none"));
  return byDow;
}

function childrenSection(all, current, legacy) {
  const last = current[current.length - 1];
  const withKids = current.filter((d) => d.juv > 0).length;
  const peak = all.reduce((b, d) => (d.juv > b.juv ? d : b), all[0]);
  const curPeak = current.reduce((b, d) => (d.juv > b.juv ? d : b), current[0]);
  const mean = current.reduce((s, d) => s + d.juv, 0) / current.length;
  const byFac = FACILITIES.filter((f) => f.eras !== "legacy").map((f) => ({ f, days: current.filter((d) => d.facilities[f.key]?.juv > 0).length, max: Math.max(...current.map((d) => d.facilities[f.key]?.juv || 0)) })).filter((x) => x.days > 0).sort((a, b) => b.days - a.days);
  const top = byFac[0];
  const topShare = top ? Math.round((100 * current.reduce((s, d) => s + (d.facilities[top.f.key]?.juv || 0), 0)) / Math.max(1, current.reduce((s, d) => s + d.juv, 0))) : 0;
  $("#kids-h").innerHTML = last.juv > 0
    ? `On ${longDate(last.date)}, <em>${fmt(last.juv)}</em> ${last.juv === 1 ? "child was" : "children were"} held in Philadelphia's adult jails.`
    : `On ${longDate(last.date)} no children were held in Philadelphia's adult jails. That is rare.`;
  $("#kids-lede").innerHTML = `The census counts juveniles held in adult facilities as their own line. In the daily record there has been at least one on <strong>${fmt(withKids)} of ${fmt(current.length)} days</strong>, an average of ${mean.toFixed(1)} a day, with a peak of <strong>${fmt(curPeak.juv)}</strong> on ${shortDate(curPeak.date)}. The 2013–2017 record peaked at <strong>${fmt(peak.juv)}</strong> on ${shortDate(peak.date)}.${top ? ` <strong>${topShare}%</strong> of them, across the daily record, were at ${facName(top.f)}, a unit that holds almost no adults.` : ""}`;
  $("#kids-facs").innerHTML = byFac.map((x) => `<div class="tile"><div class="label">${facName(x.f)}</div><div class="value">${fmt(x.days)}<small>days with a child held</small></div><div class="foot">Most at once: ${fmt(x.max)}</div></div>`).join("");
  lineChart({ id: "kids", days: all.filter((d) => d.era === "current" || d.juv > 0), value: (d) => d.juv, color: css("--juv"), zero: true, eras: true, hoverPill: $("#children .how") });
}

function tiles(days) {
  const mean = (k) => days.reduce((s, d) => s + d[k], 0) / days.length;
  const max = (k) => days.reduce((b, d) => (d[k] > b[k] ? d : b), days[0]);
  const items = [
    { k: "hosp", label: "In a hospital open ward" }, { k: "trip", label: "Out on an emergency trip" },
    { k: "out", label: "On furlough or work release" }, { k: "away", label: "Held by another jurisdiction" },
  ];
  $("#tiles").innerHTML = items.map((it) => { const m = max(it.k); const v = mean(it.k); return `<div class="tile"><div class="label">${it.label}</div><div class="value">${v < 10 ? v.toFixed(1) : fmt(v)}<small>people a day</small></div><div class="foot">Most on one day: ${fmt(m[it.k])} on ${shortDate(m.date)}</div></div>`; }).join("");
}

function findings(all, current, legacy, byDow) {
  const first = all[0], last = all[all.length - 1];
  const peak = all.reduce((b, d) => (d.total > b.total ? d : b), all[0]);
  const low = all.reduce((b, d) => (d.total < b.total ? d : b), all[0]);
  const c0 = current[0], c1 = current[current.length - 1];
  const rcfPct = pct(c0.facilities.rcf.total, c1.facilities.rcf.total);
  const cfcfShare = Math.round((100 * c1.facilities.cfcf.total) / Object.values(c1.facilities).reduce((s, f) => s + f.total, 0));
  const lehighConst = current.every((d) => d.lehigh === c1.lehigh);
  const juvMax = current.reduce((b, d) => (d.juv > b.juv ? d : b), current[0]);
  const juvDays = current.filter((d) => d.juv > 0).length;
  const legJuvMax = legacy.length ? legacy.reduce((b, d) => (d.juv > b.juv ? d : b), legacy[0]) : null;
  const womenThen = legacy.length ? (100 * legacy[0].females) / legacy[0].total : null;
  const womenNow = (100 * c1.females) / c1.total;
  const sun = byDow[0], wed = byDow[3];
  const hoc = legacy.filter((d) => d.facilities.hoc?.total);
  const missing = daysBetween(c0.date, c1.date) + 1 - current.length;
  const ratio = Math.round(PHILLY_POP / last.total);
  const swing = current.slice(1).map((d, i) => ({ d, delta: d.total - current[i].total, adj: daysBetween(current[i].date, d.date) === 1 })).filter((x) => x.adj).reduce((b, x) => (Math.abs(x.delta) > Math.abs(b.delta) ? x : b));
  const items = [
    { big: `<em>${signed(pct(first.total, last.total))}%</em> since ${parseDate(first.date).getUTCFullYear()}`, text: `On ${shortDate(first.date)} the city held ${fmt(first.total)} people. On ${shortDate(last.date)} it held ${fmt(last.total)}. The most on record is ${fmt(peak.total)} (${shortDate(peak.date)}); the fewest, ${fmt(low.total)} (${shortDate(low.date)}).` },
    { big: `One in <em>${fmt(ratio)}</em>`, text: `That is how many Philadelphians, by the 2020 Census count of ${fmt(PHILLY_POP)}, were held on ${shortDate(last.date)}.` },
    hoc.length ? { big: `<em>${fmt(hoc[0].facilities.hoc.total)}</em> at the House of Correction`, text: `That was the count on ${shortDate(hoc[0].date)}. The House of Correction no longer appears in the census at all.` } : null,
    { big: `<em>${signed(rcfPct)}%</em> at Riverside`, text: `Riverside Correctional Facility (RCF) went from ${fmt(c0.facilities.rcf.total)} to ${fmt(c1.facilities.rcf.total)} people since ${shortDate(c0.date)}, the steepest change of any building still in use. Curran-Fromhold Correctional Facility (CFCF) alone now holds ${cfcfShare}% of everyone in a city facility.` },
    { big: `<em>${fmt(c1.lehigh)}</em> in Lehigh County`, text: lehighConst ? `The same number on every one of the ${fmt(current.length)} days of the daily record. Whoever they are, they have been in Lehigh County's jail for the whole life of this dataset.` : `Held in Lehigh County on ${shortDate(c1.date)}.` },
    { big: `Up to <em>${fmt(juvMax.juv)}</em> juveniles`, text: `Juveniles were held in adult facilities on ${fmt(juvDays)} of ${fmt(current.length)} days since ${shortDate(c0.date)}, peaking at ${fmt(juvMax.juv)} on ${shortDate(juvMax.date)}.${legJuvMax ? ` In the 2013–2017 record the peak was ${fmt(legJuvMax.juv)}.` : ""}` },
    { big: `<em>${womenNow.toFixed(1)}%</em> women`, text: `${fmt(c1.females)} women and ${fmt(c1.males)} men on ${shortDate(c1.date)}.${womenThen != null ? ` In ${MONTHS[parseDate(legacy[0].date).getUTCMonth()]} ${parseDate(legacy[0].date).getUTCFullYear()} women were ${womenThen.toFixed(1)}% of a much larger count.` : ""}` },
    { big: `<em>${signed(sun.mean - wed.mean)}</em> on Sundays`, text: `Sundays average ${fmt(sun.mean)} people and Wednesdays ${fmt(wed.mean)}. People arrested over a weekend wait for a Monday hearing.` },
    { big: `<em>${fmt(Math.abs(swing.delta))}</em> in one night`, text: `The biggest overnight change in the daily record: ${swing.delta > 0 ? "up" : "down"} ${fmt(Math.abs(swing.delta))} people going into ${shortDate(swing.d.date)}.` },
    { big: `<em>${fmt(all.length)}</em> days recorded`, text: `${fmt(legacy.length)} days from the first scraper, 2013 to 2017, and ${fmt(current.length)} from the daily record since ${shortDate(c0.date)}, which has ${fmt(missing)} days missing. Gaps show as breaks in the lines.` },
  ].filter(Boolean);
  $("#findings-grid").innerHTML = items.map((it) => `<div class="finding"><div class="big">${it.big}</div><p>${it.text}</p></div>`).join("");
}

function tableView(day) {
  const r = day.raw, g = (k) => (r[k] === "" ? "–" : fmt(n(r[k])));
  const rows = (table, keys, names, cols) => `<table><caption>${table}</caption><thead><tr><th></th>${cols.map((c) => `<th>${c[0]}</th>`).join("")}</tr></thead><tbody>${keys.map((k, i) => `<tr><td>${names[i]}</td>${cols.map((c) => `<td>${g(`${c[1]}.${k}.${c[2]}`)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  const facKeys = [...CURRENT_FACS.map((f) => f.key), "rcf_asdcu", "rcf_asdmod3", "weekenders", "total"];
  const facNames = [...CURRENT_FACS.map(facName), "Riverside Correctional Facility Alternative and Special Detention Central Unit (RCF ASDCU)", "Riverside Correctional Facility Alternative and Special Detention Modular Unit (RCF ASDMOD3)", "Weekenders program", "Total"];
  $("#table-summary").textContent = `The ${shortDate(day.date)} census as a table`;
  $("#table-inner").innerHTML =
    rows("In facility", facKeys, facNames, [["Adult men", "in_facility", "adult_males"], ["Adult women", "in_facility", "adult_females"], ["Juvenile boys", "in_facility", "juvenile_males"], ["Juvenile girls", "in_facility", "juvenile_females"]]) +
    rows("Temporarily not in facility", facKeys, facNames, [["Workers", "temporarily_not_in_facility", "male_workers"], ["Furlough", "temporarily_not_in_facility", "male_furlough"], ["Open ward, men", "temporarily_not_in_facility", "male_open_ward"], ["Open ward, women", "temporarily_not_in_facility", "female_open_ward"], ["Trips, men", "temporarily_not_in_facility", "male_emergency_trips"], ["Trips, women", "temporarily_not_in_facility", "female_emergency_trips"]]) +
    rows("Facility totals", facKeys, facNames, [["Men", "facility_totals", "males"], ["Women", "facility_totals", "females"], ["Total", "facility_totals", "total"]]) +
    rows("Held in other jurisdictions", ["state_doc", "juveniles", "delaware_county", "lehigh_county", "all_other", "total"], ["State Department of Corrections", "Juveniles", "Delaware County", "Lehigh County", "All other jurisdictions", "Total"], [["Men", "other_jurisdictions", "males"], ["Women", "other_jurisdictions", "females"], ["Total", "other_jurisdictions", "total"]]) +
    rows("Total population", ["pdp_facilities", "other_jurisdictions", "total"], ["In or temporarily out of a city facility", "Held by other jurisdictions", "Total"], [["Men", "total_population", "males"], ["Women", "total_population", "females"], ["Total", "total_population", "total"]]);
}

function drawMainCharts() {
  const all = state.days, current = all.filter((d) => d.era === "current");
  const value = (d) => headcount(d, state.facility);
  const series = state.facility ? all.filter((d) => d.facilities[state.facility]) : all;
  if (series.length > 1) lineChart({ id: "long", days: series, value, color: css("--accent"), zero: true, eras: true, hoverPill: $("#long .how") });
  const cur = state.facility ? current.filter((d) => d.facilities[state.facility]) : current;
  if (cur.length > 1) lineChart({ id: "total", days: cur, value, color: css("--accent"), hoverPill: $("#trend .how") });
  yearBars(series);
  markCharts(all[state.idx].date);
}

// ---------------------------------------------------------------- chrome

function wireChrome() {
  const btn = $("#menu-btn"), nav = $("#site-nav");
  btn.addEventListener("click", () => { const open = nav.classList.toggle("open"); btn.setAttribute("aria-expanded", String(open)); });
  nav.addEventListener("click", (e) => { if (e.target.tagName === "A") { nav.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); } });
  const top = $("#totop");
  addEventListener("scroll", () => top.classList.toggle("show", scrollY > 600), { passive: true });
  top.addEventListener("click", () => { scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" }); $(".brand").focus(); });
}

// ---------------------------------------------------------------- boot

async function main() {
  wireChrome();
  const status = $("#status");
  let currentRows, legacyRows = [];
  try { currentRows = await fetchCsv(SOURCES.current); } catch (err) {
    $("#hero-h1").textContent = "The census could not be loaded."; status.textContent = `Could not fetch census.csv (${err.message}). Try again in a minute.`; return;
  }
  try { legacyRows = await fetchCsv(SOURCES.legacy); } catch { status.textContent = "The 2013–2017 record could not be loaded; showing the daily record only."; }

  const current = currentRows.map(currentDay).filter((d) => d.total > 0);
  const legacy = legacyRows.map(legacyDay).filter((d) => d.total > 0);
  const all = [...legacy, ...current].sort((a, b) => a.date.localeCompare(b.date));
  state.days = all;
  const last = all[all.length - 1], first = all[0];
  wall.colors = KINDS.map((k) => css(k.css));

  $("#hero-h1").innerHTML = `Right now Philadelphia holds <em>${fmt(last.total)}</em> people in its jails.`;
  $("#hero-eyebrow-date").textContent = `Latest census: ${longDate(last.date)}`;
  $("#hero-sub").innerHTML = (legacy.length ? `On ${shortDate(first.date)} it held <strong>${fmt(first.total)}</strong>. ` : "")
    + `<span id="hero-symbol">Every symbol below is one person counted that day.</span> Press play to watch the years go by, drag the timeline, or pick a date.`;
  $("#hero-eyebrow").textContent = `Philadelphia Department of Prisons · ${fmt(all.length)} census days recorded since ${shortDate(first.date)}`;
  document.title = `JailJawn · ${fmt(last.total)} people`;

  try { await Promise.all([document.fonts.load(`12px ${ICON_FONT}`), document.fonts.load('600 14px "Public Sans"')]); } catch { /* fall back */ }

  wireControls();
  showLatestCrowd();
  drawMainCharts();
  const byDow = dowChart(current);
  facilityPanels(all);
  tiles(current);
  childrenSection(all, current, legacy);
  findings(all, current, legacy, byDow);
  const ld = $("#ld-dataset");
  if (ld) { try { const j = JSON.parse(ld.textContent); j.temporalCoverage = `${first.date}/${last.date}`; j.dateModified = last.date; ld.textContent = JSON.stringify(j); } catch { /* leave as is */ } }
  tableView(current[current.length - 1]);

  const c0 = current[0], c1 = current[current.length - 1];
  $("#long-lede").innerHTML = legacy.length ? `In ${MONTHS[parseDate(first.date).getUTCMonth()]} ${parseDate(first.date).getUTCFullYear()} the city's jails held <strong>${fmt(first.total)}</strong> people. On ${shortDate(last.date)} they held <strong>${fmt(last.total)}</strong>, ${Math.abs(pct(first.total, last.total))}% ${last.total < first.total ? "fewer" : "more"}. The record between is patchy, then goes dark for eight years, then becomes daily.` : "";
  $("#trend-lede").innerHTML = `Since ${shortDate(c0.date)} the daily count has moved from <strong>${fmt(c0.total)}</strong> to <strong>${fmt(c1.total)}</strong>, ${pct(c0.total, c1.total) < 0 ? "down" : "up"} ${Math.abs(pct(c0.total, c1.total))}%. Hover or tap the line for any day; tap to jump the crowd to it.`;
  $("#fac-lede").innerHTML = `Five buildings hold nearly everyone today. Riverside Correctional Facility (RCF) went from <strong>${fmt(c0.facilities.rcf.total)}</strong> to <strong>${fmt(c1.facilities.rcf.total)}</strong> people since ${shortDate(c0.date)}, while the Philadelphia Industrial Correctional Center (PICC) barely moved, ${fmt(c0.facilities.picc.total)} to ${fmt(c1.facilities.picc.total)}.`;
  $("#dow-sub").textContent = `Sundays average ${fmt(byDow[0].mean)} people and Wednesdays ${fmt(byDow[3].mean)}, across the daily record. People arrested over a weekend wait for a Monday hearing.`;

  const hash = location.hash.replace("#", "");
  const startIdx = /^\d{4}-\d{2}-\d{2}$/.test(hash) ? nearestIdx(hash) : all.length - 1;
  showDay(startIdx);
  status.textContent = `Latest census: ${longDate(last.date)}. The data refreshes from the repository each time this page loads.`;
}

main();
