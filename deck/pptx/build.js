// Export the HTML slide deck in ../project to an editable PowerPoint file.
//
// Each slide is laid out in headless Chromium at 1920x1080, then every box,
// border, text block, shape and icon is read back and rebuilt as a native
// PowerPoint shape or text box at the same position. The annual costs bar
// chart is rebuilt as a native PowerPoint chart from ../data/annual_balancing_costs.csv.
// Speaker notes come from each slide's <aside>; slides marked `hidden` in the
// HTML are hidden in PowerPoint; sections follow project/deck.json.
//
// Usage (from deck/pptx):  npm install && node build.js [deck folder] [output .pptx]
// Defaults: ../ (this deck) -> deck/balancing-the-grid.pptx.
// The restyled copy: node build.js ../../deck-alt ../../deck-alt/balancing-the-grid-corporate.pptx

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const JSZip = require("jszip");
const sharp = require("sharp");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const Pi = require("react-icons/pi");

let chromium;
try { ({ chromium } = require("playwright")); }
catch { ({ chromium } = require(path.join(require("child_process").execSync("npm root -g").toString().trim(), "playwright"))); }

const DECK = path.resolve(process.argv[2] || path.join(__dirname, ".."));
const PROJECT = path.join(DECK, "project");
const OUT = path.resolve(process.argv[3] || path.join(DECK, "balancing-the-grid.pptx"));
const COSTS_CSV = path.join(__dirname, "../data/annual_balancing_costs.csv");
const FONT = "Arial"; // IBM Plex Sans and Space Grotesk are not on most Office installs
const PX = 1 / 144; // 1920px canvas -> 13.333in slide
const PT = 0.5; // px -> pt

const ICONS = { Lightning: "PiLightning", Lightbulb: "PiLightbulb", Factory: "PiFactory", Search: "PiMagnifyingGlass" };

const BASE_CSS = `
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;background:#fff}
section{position:relative;width:1920px;height:1080px;overflow:hidden;font-family:${FONT}}
h1{font-size:96px;font-weight:600;line-height:1.1} h2{font-size:64px;font-weight:600;line-height:1.15} h3{font-size:44px;font-weight:600;line-height:1.2}
p,ul,ol{line-height:1.4} ul,ol{padding-left:1.2em}
td,th{padding:0.35em 0.6em;border-bottom:1px solid #D9D4C7;text-align:left;vertical-align:top}
th{font-weight:600}
aside{display:none}
x-shape,x-icon{display:block;flex-shrink:0}
table{border-collapse:collapse}
`;

// ---------- browser-side extraction ----------
function extract() {
  const sec = document.querySelector("section");
  const S = sec.getBoundingClientRect();
  const out = { shapes: [], texts: [], icons: [], tables: [], chart: null };
  const rgb = (c) => {
    const m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    if (!m) return null;
    const a = m[4] === undefined ? 1 : +m[4];
    if (a === 0) return null;
    const hex = [m[1], m[2], m[3]].map((v) => (+v).toString(16).padStart(2, "0")).join("").toUpperCase();
    return { hex, a };
  };
  const box = (r) => ({ x: r.left - S.left, y: r.top - S.top, w: r.width, h: r.height });

  // Native-chart stand-in: the annual costs bar chart
  let chartEl = null;
  if (sec.id === "annualcosts") {
    chartEl = sec.querySelector('[style*="border-bottom:2px solid"]').parentElement;
    out.chart = box(chartEl.getBoundingClientRect());
    // Take the chart's colours from the HTML so each deck style keeps its own palette
    const bars = chartEl.querySelector('[style*="border-bottom:2px solid"]');
    const first = bars.children[0].lastElementChild.children;
    const dashed = bars.querySelector('[style*="dashed"]');
    const dcs = getComputedStyle(dashed);
    out.chart.colors = {
      con: rgb(getComputedStyle(first[first.length - 1]).backgroundColor).hex,
      oth: rgb(getComputedStyle(first[0]).backgroundColor).hex,
      fcLine: rgb(dcs.borderTopColor).hex,
      fcFill: (rgb(dcs.backgroundColor) || { hex: "FFFFFF" }).hex,
      patterned: dcs.backgroundImage !== "none",
      label: rgb(getComputedStyle(bars.querySelector("p")).color).hex,
      axis: rgb(getComputedStyle(bars).borderBottomColor).hex,
      text: rgb(getComputedStyle(chartEl.querySelector("p")).color).hex,
    };
  }

  const TEXT_TAGS = new Set(["P", "H1", "H2", "H3", "LI", "TD", "TH"]);
  const INLINE = new Set(["B", "I", "U", "SPAN", "A", "BR", "STRONG", "EM"]);

  function runsOf(el) {
    const runs = [];
    const walk = (node) => {
      for (const n of node.childNodes) {
        if (n.nodeType === 3) {
          const cs = getComputedStyle(n.parentElement);
          let t = n.textContent.replace(/\s+/g, " ");
          if (cs.textTransform === "uppercase") t = t.toUpperCase();
          if (t) runs.push({ text: t, color: rgb(cs.color), bold: +cs.fontWeight >= 600, italic: cs.fontStyle === "italic", underline: cs.textDecorationLine.includes("underline") });
        } else if (n.nodeName === "BR") {
          runs.push({ br: true });
        } else if (n.nodeType === 1 && INLINE.has(n.nodeName)) {
          walk(n);
        }
      }
    };
    walk(el);
    // trim whitespace at line starts / ends
    const lines = [[]];
    for (const r of runs) r.br ? lines.push([]) : lines[lines.length - 1].push(r);
    for (const ln of lines) {
      if (ln.length) { ln[0].text = ln[0].text.replace(/^ /, ""); ln[ln.length - 1].text = ln[ln.length - 1].text.replace(/ $/, ""); }
    }
    return lines.map((ln) => ln.filter((r) => r.text !== ""));
  }

  function visit(el) {
    if (el === chartEl || el.nodeName === "ASIDE") return;
    const cs = getComputedStyle(el);
    if (cs.display === "none") return;
    const r = el.getBoundingClientRect();
    const b = box(r);

    if (el.nodeName === "X-ICON") {
      out.icons.push({ ...b, name: el.getAttribute("name"), color: rgb(cs.color) });
      return;
    }
    if (el.nodeName === "X-SHAPE") {
      out.shapes.push({ ...b, kind: el.getAttribute("kind"), fill: rgb(cs.backgroundColor) });
      return;
    }

    if (el.nodeName === "TABLE") {
      const rows = [...el.rows].map((tr) => {
        const tcs = getComputedStyle(tr);
        return {
          h: tr.getBoundingClientRect().height,
          fill: rgb(tcs.backgroundColor),
          cells: [...tr.cells].map((td) => {
            const c = getComputedStyle(td);
            return {
              lines: runsOf(td), align: c.textAlign === "center" || c.textAlign === "right" ? c.textAlign : "left",
              pad: ["Top", "Right", "Bottom", "Left"].map((s) => parseFloat(c["padding" + s]) || 0),
              fontSize: parseFloat(c.fontSize), lineHeight: c.lineHeight === "normal" ? parseFloat(c.fontSize) * 1.2 : parseFloat(c.lineHeight),
              rule: rgb(c.borderBottomColor), ruleW: parseFloat(c.borderBottomWidth) || 0,
            };
          }),
        };
      });
      const colW = [...el.rows[0].cells].map((td) => td.getBoundingClientRect().width);
      out.tables.push({ ...b, fill: rgb(cs.backgroundColor), rows, colW });
      return;
    }

    if (el !== sec) {
      const fill = rgb(cs.backgroundColor);
      const sides = ["Top", "Right", "Bottom", "Left"].map((s) => ({
        w: parseFloat(cs["border" + s + "Width"]) || 0,
        color: rgb(cs["border" + s + "Color"]),
        style: cs["border" + s + "Style"],
      })).map((s) => (s.style === "none" || !s.color ? { w: 0 } : s));
      const radius = parseFloat(cs.borderTopLeftRadius) || 0;
      if (fill || sides.some((s) => s.w > 0)) out.shapes.push({ ...b, kind: "box", fill, sides, radius });
    }

    const hasText = el.textContent.trim() && ![...el.children].some((c) => !INLINE.has(c.nodeName));
    if (TEXT_TAGS.has(el.nodeName) && hasText) {
      const pad = ["Top", "Right", "Bottom", "Left"].map((s) => (parseFloat(cs["padding" + s]) || 0) + (parseFloat(cs["border" + s + "Width"]) || 0));
      const fs = parseFloat(cs.fontSize);
      const lh = cs.lineHeight === "normal" ? fs * 1.2 : parseFloat(cs.lineHeight);
      let bullet = null;
      let x = b.x + pad[3];
      if (el.nodeName === "LI") {
        const ul = el.parentElement.getBoundingClientRect();
        bullet = { indent: r.left - ul.left };
        x = ul.left - S.left;
      }
      const w = b.x + b.w - pad[1] - x;
      out.texts.push({
        x, y: b.y + pad[0], w, h: b.h - pad[0] - pad[2],
        lines: runsOf(el), fontSize: fs, lineHeight: lh,
        align: ["center", "right"].includes(cs.textAlign) ? cs.textAlign : "left",
        charSpacing: parseFloat(cs.letterSpacing) || 0,
        nowrap: cs.whiteSpace === "nowrap",
        heading: /^H[12]$/.test(el.nodeName),
        bullet,
      });
      return; // inline children already consumed
    }
    for (const c of el.children) visit(c);
  }
  out.background = rgb(getComputedStyle(sec).backgroundColor);
  out.hidden = sec.hasAttribute("hidden");
  visit(sec);
  return out;
}

// ---------- PowerPoint side ----------
const inch = (px) => +(px * PX).toFixed(4);

async function iconPng(name, color) {
  const comp = Pi[ICONS[name]] || Pi.PiCircle;
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(comp, { color: "#" + color, size: 256 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

function addBox(slide, pres, s, n) {
  const { x, y, w, h, fill, sides, radius } = s;
  const shapeFor = (r) => (r > 0 ? pres.ShapeType.roundRect : pres.ShapeType.rect);
  const opts = (bx, by, bw, bh, f, line) => {
    const o = { x: inch(bx), y: inch(by), w: inch(bw), h: inch(bh), objectName: `box ${n}` };
    o.fill = f ? { color: f.hex, transparency: Math.round((1 - f.a) * 100) } : { type: "none" };
    o.line = line ? { color: line.color.hex, width: Math.max(0.5, line.w * PT), dashType: line.style === "dashed" ? "dash" : "solid" } : { type: "none" };
    if (radius > 0) o.rectRadius = Math.min(radius, bw / 2, bh / 2) * PX;
    return o;
  };
  const on = sides.filter((sd) => sd.w > 0);
  const same = (a, b2) => a.w === b2.w && a.color && b2.color && a.color.hex === b2.color.hex;
  const uniform = on.length === 4 && on.every((sd) => same(sd, on[0]));
  if (on.length === 0 || uniform) {
    slide.addShape(shapeFor(radius), opts(x, y, w, h, fill, uniform ? on[0] : null));
    return;
  }
  // Non-uniform borders: a thin outline on most sides plus one or more accent sides
  const counts = {};
  on.forEach((sd) => { const k = sd.w + sd.color.hex; counts[k] = (counts[k] || 0) + 1; });
  const thinKey = Object.keys(counts).find((k) => counts[k] >= 3);
  const thin = thinKey ? on.find((sd) => sd.w + sd.color.hex === thinKey) : null;
  const accents = sides.map((sd, i) => ({ ...sd, i })).filter((sd) => sd.w > 0 && !(thin && same(sd, thin)));

  if (radius > 0 && fill && accents.length === 1) {
    // Outer rounded shape in the accent colour, inner one in the fill, so the accent follows the corners
    const a = accents[0];
    slide.addShape(shapeFor(radius), opts(x, y, w, h, a.color, null));
    const ins = [0, 0, 0, 0]; ins[a.i] = a.w;
    slide.addShape(shapeFor(radius), opts(x + ins[3], y + ins[0], w - ins[1] - ins[3], h - ins[0] - ins[2], fill, thin));
    return;
  }
  if (fill || thin) slide.addShape(shapeFor(radius), opts(x, y, w, h, fill, thin));
  for (const a of accents) {
    const r = [
      [x, y, w, a.w], [x + w - a.w, y, a.w, h], [x, y + h - a.w, w, a.w], [x, y, a.w, h],
    ][a.i];
    if (a.style === "dashed") {
      const horiz = a.i % 2 === 0;
      const ly = horiz ? r[1] + a.w / 2 : r[1];
      const lx = horiz ? r[0] : r[0] + a.w / 2;
      slide.addShape(pres.ShapeType.line, { x: inch(lx), y: inch(ly), w: horiz ? inch(r[2]) : 0, h: horiz ? 0 : inch(r[3]), line: { color: a.color.hex, width: a.w * PT, dashType: "dash" } });
    } else {
      slide.addShape(pres.ShapeType.rect, { x: inch(r[0]), y: inch(r[1]), w: inch(r[2]), h: inch(r[3]), fill: { color: a.color.hex }, line: { type: "none" }, objectName: `border ${n}` });
    }
  }
}

function addTextBlock(slide, t, n) {
  const runs = [];
  t.lines.forEach((ln, li) => {
    ln.forEach((r, ri) => {
      const o = { color: r.color ? r.color.hex : "1B2638", bold: r.bold, italic: r.italic };
      if (r.underline) o.underline = { style: "sng" };
      if (ri === ln.length - 1 && li < t.lines.length - 1) o.breakLine = true;
      runs.push({ text: r.text, options: o });
    });
    if (ln.length === 0 && li < t.lines.length - 1) runs.push({ text: "", options: { breakLine: true } });
  });
  if (!runs.length) return;
  const singleLine = t.lines.length === 1 && t.h < t.lineHeight * 1.5;
  // Slack for small metric differences between Chromium and PowerPoint
  const slack = singleLine ? 0.08 : 0.002;
  let x = t.x, w = t.w * (1 + slack);
  if (t.align === "center") x -= (t.w * slack) / 2;
  if (t.align === "right") x -= t.w * slack;
  const o = {
    x: inch(x), y: inch(t.y), w: inch(w), h: inch(t.h),
    fontFace: FONT, fontSize: +(t.fontSize * PT).toFixed(1),
    lineSpacing: +(t.lineHeight * PT).toFixed(1),
    align: t.align, valign: "top", margin: 0, isTextBox: true,
    wrap: !(t.nowrap || singleLine), fit: "none", objectName: `text ${n}`,
  };
  if (t.charSpacing) o.charSpacing = +(t.charSpacing * PT).toFixed(2);
  if (t.bullet) {
    runs.forEach((r) => { r.options.bullet = { indent: +(t.bullet.indent * PT).toFixed(1) }; });
      }
  slide.addText(runs, o);
}

function cellRuns(lines) {
  const runs = [];
  lines.forEach((ln, li) => ln.forEach((r, ri) => {
    const o = { color: r.color ? r.color.hex : "1B2638", bold: r.bold, italic: r.italic };
    if (ri === ln.length - 1 && li < lines.length - 1) o.breakLine = true;
    runs.push({ text: r.text, options: o });
  }));
  return runs;
}

function addNativeTable(slide, t, n) {
  const rows = t.rows.map((row) => row.cells.map((c) => {
    const fill = row.fill || t.fill;
    const rule = c.ruleW ? { type: "solid", pt: Math.max(0.5, c.ruleW * PT), color: c.rule.hex } : { type: "none" };
    return {
      text: cellRuns(c.lines),
      options: {
        fill: fill ? { color: fill.hex } : undefined,
        align: c.align, valign: "top", fontFace: FONT, fontSize: +(c.fontSize * PT).toFixed(1),
        lineSpacing: +(c.lineHeight * PT).toFixed(1),
        margin: c.pad.map((v) => +(v * PX).toFixed(3)),
        border: [{ type: "none" }, { type: "none" }, rule, { type: "none" }],
      },
    };
  }));
  slide.addTable(rows, {
    x: inch(t.x), y: inch(t.y), w: inch(t.w),
    colW: t.colW.map(inch), rowH: t.rows.map((r) => inch(r.h)), autoPage: false, objectName: `table ${n}`,
  });
}

function readCosts() {
  const rows = fs.readFileSync(COSTS_CSV, "utf8").trim().split("\n").slice(1)
    .map((l) => l.match(/("[^"]*"|[^,]*)(,|$)/g).map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "")));
  const byYear = {};
  for (const [year, status, con, oth, tot] of rows) {
    const y = (byYear[year] = byYear[year] || { con: null, oth: null, fc: null });
    if (status.startsWith("actual")) { y.con = +con / 1000; y.oth = +oth / 1000; }
    else y.fc = (y.fc || 0) + +tot / 1000;
  }
  return byYear;
}

let chartColors = null;
function addCostsChart(slide, pres, rect) {
  const C = (chartColors = rect.colors);
  const d = readCosts();
  const years = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "’28–29", "2030"];
  const g = (y, k) => (d[y] && d[y][k] != null ? +d[y][k].toFixed(3) : 0);
  const con = years.map((y) => g(y, "con"));
  const oth = years.map((y) => g(y, "oth"));
  const fc = years.map((y) => g(y, "fc"));
  const tot = years.map((_, i) => +(con[i] + oth[i] + fc[i]).toFixed(3));

  slide.addText("GB balancing costs by calendar year, £bn", {
    x: inch(rect.x), y: inch(rect.y), w: inch(rect.w * 0.5), h: 0.3, fontFace: FONT, fontSize: 12, color: C.text,
    margin: 0, valign: "top", isTextBox: true, objectName: "chart caption",
  });
  const axis = { catAxisLabelColor: C.text, catAxisLabelFontSize: 11, catAxisLabelFontFace: FONT };
  slide.addChart(
    [
      { type: pres.ChartType.bar, data: [
        { name: "Constraints", labels: years, values: con },
        { name: "Everything else", labels: years, values: oth },
        { name: "NESO forecast", labels: years, values: fc },
      ], options: { barGrouping: "stacked", chartColors: [C.con, C.oth, C.fcLine], barGapWidthPct: 55 } },
      { type: pres.ChartType.line, data: [{ name: "Total", labels: years, values: tot }], options: {
        chartColors: [C.label], lineSize: 0, lineDataSymbol: "none",
        showValue: true, dataLabelPosition: "t", dataLabelFormatCode: '[>7.5]"~"0;[=0]"";0.0',
        dataLabelColor: C.label, dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelFontFace: FONT,
      } },
    ],
    {
      x: inch(rect.x), y: inch(rect.y) + 0.3, w: inch(rect.w), h: inch(rect.h) - 0.3,
      showLegend: true, legendPos: "t", layout: { x: 0, y: 0.1, w: 1, h: 0.9 }, legendFontSize: 12, legendColor: C.text, legendFontFace: FONT,
      valAxisHidden: true, valGridLine: { style: "none" }, valAxisMinVal: 0, valAxisMaxVal: 8.6,
      catAxisLineShow: true, catAxisLineColor: C.axis, catGridLine: { style: "none" }, ...axis,
      objectName: "Annual balancing costs chart",
      altText: "Stacked columns of GB balancing costs by calendar year, 2018 to 2026 actuals split into constraints and everything else, with NESO forecasts for Nov-Dec 2026, 2027 and 2030.",
    }
  );
}

// Patch chart XML: patterned, dashed forecast series; invisible total line; total hidden from legend.
async function patchCharts(file) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  for (const name of Object.keys(zip.files).filter((n) => /ppt\/charts\/chart\d+\.xml$/.test(n))) {
    let xml = await zip.file(name).async("string");
    if (!xml.includes("NESO forecast")) continue;
    xml = xml.replace(/(<c:ser>(?:(?!<\/c:ser>).)*?NESO forecast(?:(?!<\/c:ser>).)*?<c:spPr>)(.*?)(<\/c:spPr>)/s, (m, a, _sp, c) =>
      a + (chartColors.patterned
        ? `<a:pattFill prst="wdUpDiag"><a:fgClr><a:srgbClr val="${chartColors.fcLine}"/></a:fgClr><a:bgClr><a:srgbClr val="FFFDF8"/></a:bgClr></a:pattFill>`
        : `<a:solidFill><a:srgbClr val="${chartColors.fcFill}"/></a:solidFill>`) +
      `<a:ln w="19050"><a:solidFill><a:srgbClr val="${chartColors.fcLine}"/></a:solidFill><a:prstDash val="dash"/></a:ln>` + c);
    xml = xml.replace(/(<c:lineChart>.*?<c:ser>.*?<c:spPr>)(.*?)(<\/c:spPr>)/s, (m, a, _sp, c) => a + '<a:ln><a:noFill/></a:ln>' + c);
    xml = xml.replace(/<c:legend>\s*<c:legendPos val="t"\/>/, '<c:legend><c:legendPos val="t"/><c:legendEntry><c:idx val="3"/><c:delete val="1"/></c:legendEntry>');
    zip.file(name, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

async function main() {
  const deck = JSON.parse(fs.readFileSync(path.join(PROJECT, "deck.json"), "utf8"));
  const sectionStarts = {};
  for (const s of Object.values(deck.sections || {})) sectionStarts[s.start] = s.description;

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = deck.title;
  pres.author = "Matt";
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  let section = null;
  let n = 0;
  for (const id of deck.order) {
    let html = fs.readFileSync(path.join(PROJECT, "slides", id + ".html"), "utf8");
    html = html.replace(/'(Space Grotesk|IBM Plex Sans)'/g, FONT);
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${BASE_CSS}</style></head><body>${html}</body></html>`);
    const hidden = await page.evaluate(() => { const s = document.querySelector("section"); const h = s.hasAttribute("hidden"); s.removeAttribute("hidden"); return h; });
    const spec = await page.evaluate(extract);
    const notes = await page.evaluate(() => (document.querySelector("aside")?.textContent || "").replace(/\s+/g, " ").trim());

    if (sectionStarts[id]) { section = sectionStarts[id]; pres.addSection({ title: section }); }
    const slide = pres.addSlide(section ? { sectionTitle: section } : {});
    slide.background = { color: spec.background ? spec.background.hex : "FFFFFF" };
    if (hidden) slide.hidden = true;

    for (const s of spec.shapes) {
      n++;
      if (s.kind === "box") addBox(slide, pres, s, n);
      else if (s.kind === "arrow-right") slide.addShape(pres.ShapeType.rightArrow, { x: inch(s.x), y: inch(s.y), w: inch(s.w), h: inch(s.h), fill: { color: s.fill.hex }, line: { type: "none" }, objectName: `arrow ${n}` });
      else slide.addShape(pres.ShapeType.rect, { x: inch(s.x), y: inch(s.y), w: inch(s.w), h: inch(s.h), fill: { color: s.fill ? s.fill.hex : "9AA8BC" }, line: { type: "none" }, objectName: `${s.kind} ${n}` });
    }
    for (const ic of spec.icons) {
      slide.addImage({ data: await iconPng(ic.name, ic.color ? ic.color.hex : "14213D"), x: inch(ic.x), y: inch(ic.y), w: inch(ic.w), h: inch(ic.h), altText: ic.name + " icon" });
    }
    for (const t of spec.texts) addTextBlock(slide, t, ++n);
    for (const t of spec.tables) addNativeTable(slide, t, ++n);
    if (spec.chart) addCostsChart(slide, pres, spec.chart);
    if (notes) slide.addNotes(notes);
    console.log(`${id}${hidden ? " (hidden)" : ""}: ${spec.shapes.length} shapes, ${spec.texts.length} text, ${spec.icons.length} icons, ${spec.tables.length} tables${spec.chart ? ", native chart" : ""}`);
  }
  await browser.close();
  await pres.writeFile({ fileName: OUT });
  await patchCharts(OUT);
  console.log("Wrote " + OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
