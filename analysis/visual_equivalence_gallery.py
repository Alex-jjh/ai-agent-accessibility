#!/usr/bin/env python3
"""
Visual Equivalence Gallery — Human review tool.

Generates a self-contained HTML report with side-by-side base/variant
screenshots, per-pair SSIM/pHash/MAD metrics, and a lightweight review UI
with keyboard shortcuts for flagging.

Gallery features:
  - base | low | diff mask (3-up)  per URL row
  - SSIM / pHash / MAD per pair
  - Sort: by SSIM ascending (most different first), by app, by URL
  - Filters: app, Group A/B/C/error, screenshot present
  - Per-row flags: "looks identical to me" / "clearly different" / "borderline"
    → saved to localStorage (exportable as JSON)
  - Diff visualization toggle: overlay magenta-on-base mask OR side-by-side
  - Keyboard: J next, K prev, 1/2/3 assign flag, D toggle diff, C focus comment

Also supports ablation mode:
  - 14-up grid per URL (base + 13 patches)
  - One row per URL, color-coded by Group A/B/C

Usage:
  # After analysis has run and produced per_pair_metrics.csv:
  python3 analysis/visual_equivalence_gallery.py \\
    --mode aggregate \\
    --metrics results/visual-equivalence/per_pair_metrics.csv \\
    --screenshots data/visual-equivalence/replay \\
    --output results/visual-equivalence/gallery.html

  python3 analysis/visual_equivalence_gallery.py \\
    --mode ablation \\
    --metrics results/visual-equivalence/per_patch_metrics.csv \\
    --screenshots data/visual-equivalence/ablation-replay \\
    --output results/visual-equivalence/ablation-gallery.html

The generated HTML embeds screenshots via file:// references (relative paths),
so open it directly in a browser. For cross-machine sharing, use
`--embed-base64` to inline images (much larger file but self-contained).
"""

import argparse
import base64
import csv
import json
import pathlib
import sys
from typing import Optional


HTML_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<title>Visual Equivalence Gallery — {title}</title>
<style>
  :root {{
    --green: #2a8c4a; --red: #c53030; --yellow: #d69e2e; --bg: #1a1d23;
    --panel: #252932; --text: #e8eaed; --muted: #9aa0a6;
    --border: #363a44;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system,BlinkMacSystemFont,sans-serif;
         background: var(--bg); color: var(--text); }}
  header {{ position: sticky; top: 0; z-index: 10; background: var(--panel);
            padding: 12px 20px; border-bottom: 2px solid var(--border);
            display: flex; flex-wrap: wrap; gap: 16px; align-items: center; }}
  h1 {{ margin: 0; font-size: 18px; }}
  .stats {{ color: var(--muted); font-size: 13px; }}
  .stats strong {{ color: var(--text); }}
  .controls {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
  select, input, button {{ background: var(--bg); color: var(--text);
                           border: 1px solid var(--border); padding: 4px 8px;
                           font-size: 13px; border-radius: 4px; }}
  button {{ cursor: pointer; }}
  button:hover {{ background: var(--border); }}
  .row {{ display: grid; gap: 0; padding: 12px 20px;
          border-bottom: 1px solid var(--border);
          grid-template-columns: 320px 1fr;
          transition: background 0.1s; }}
  .row:hover {{ background: #1f2229; }}
  .row.flagged-identical {{ border-left: 4px solid var(--green); }}
  .row.flagged-different {{ border-left: 4px solid var(--red); }}
  .row.flagged-borderline {{ border-left: 4px solid var(--yellow); }}
  .meta {{ padding-right: 16px; font-size: 13px; }}
  .meta .title {{ font-weight: 600; margin-bottom: 6px; word-break: break-all; }}
  .meta .url {{ color: var(--muted); font-family: monospace; font-size: 11px;
                word-break: break-all; margin-bottom: 8px; }}
  .metric-grid {{ display: grid; grid-template-columns: auto 1fr; gap: 2px 10px;
                  font-family: monospace; font-size: 12px; margin: 8px 0; }}
  .metric-grid .label {{ color: var(--muted); }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px;
            font-size: 11px; font-weight: 600; }}
  .badge-A {{ background: rgba(42,140,74,.3); color: #5fbe7f; }}
  .badge-B {{ background: rgba(197,48,48,.3); color: #e56a6a; }}
  .badge-C {{ background: rgba(155,89,182,.3); color: #c894e1; }}
  .badge-amb {{ background: rgba(214,158,46,.3); color: #eab86a; }}
  .badge-err {{ background: rgba(100,100,100,.3); color: #bbb; }}
  .shots {{ display: grid; gap: 4px; grid-template-columns: 1fr 1fr 1fr; }}
  .shot {{ position: relative; background: var(--bg); border: 1px solid var(--border);
           min-height: 200px; overflow: hidden; }}
  .shot img {{ width: 100%; height: auto; display: block; }}
  .shot .caption {{ position: absolute; top: 4px; left: 4px;
                    background: rgba(0,0,0,0.7); color: white;
                    padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
  .shot.missing {{ display: flex; align-items: center; justify-content: center;
                   color: var(--muted); font-size: 12px; min-height: 80px; }}
  .flag-buttons {{ display: flex; gap: 6px; margin-top: 10px; }}
  .flag-buttons button {{ flex: 1; }}
  .flag-buttons button.active {{ border-color: var(--text); background: var(--border); }}
  .flag-buttons .identical.active {{ background: var(--green); color: white; border-color: var(--green); }}
  .flag-buttons .different.active {{ background: var(--red); color: white; border-color: var(--red); }}
  .flag-buttons .borderline.active {{ background: var(--yellow); color: #222; border-color: var(--yellow); }}
  .comment {{ width: 100%; margin-top: 6px; font-size: 12px;
              background: var(--bg); color: var(--text);
              border: 1px solid var(--border); padding: 4px; }}
  .hotkey {{ color: var(--muted); font-size: 11px; margin-left: 4px; }}
  .export-row {{ padding: 10px 20px; background: var(--panel);
                 position: sticky; bottom: 0; border-top: 2px solid var(--border);
                 display: flex; gap: 10px; align-items: center; }}
  #progress {{ color: var(--muted); font-size: 13px; margin-left: auto; }}
  .ablation-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }}
  .ablation-shot {{ position: relative; background: var(--bg);
                    border: 1px solid var(--border); min-height: 100px; }}
  .ablation-shot img {{ width: 100%; height: auto; display: block; }}
  .ablation-shot.group-A {{ border-color: #5fbe7f; }}
  .ablation-shot.group-B {{ border-color: #e56a6a; }}
  .ablation-shot.group-C {{ border-color: #c894e1; }}
  .ablation-shot.group-err {{ border-color: #777; opacity: 0.5; }}
  .ablation-shot .caption {{ position: absolute; bottom: 2px; left: 2px;
                              background: rgba(0,0,0,0.7); color: white;
                              padding: 1px 4px; border-radius: 3px;
                              font-size: 10px; font-family: monospace; }}
  details > summary {{ cursor: pointer; padding: 4px; }}
</style>

<header>
  <h1>{title}</h1>
  <div class="stats" id="stats"></div>
  <div class="controls">
    <label>Sort:
      <select id="sort">
        <option value="ssim_asc">SSIM ↑ (most different first)</option>
        <option value="ssim_desc">SSIM ↓ (most identical first)</option>
        <option value="app">App</option>
        <option value="url">URL</option>
        <option value="group">Group</option>
      </select>
    </label>
    <label>App:
      <select id="filter-app">
        <option value="">all</option>
      </select>
    </label>
    <label>Group:
      <select id="filter-group">
        <option value="">all</option>
        <option value="A">A identical</option>
        <option value="B">B visible diff</option>
        <option value="C">C func only</option>
        <option value="ambiguous">ambiguous</option>
        <option value="error">error</option>
      </select>
    </label>
    <label>Flag:
      <select id="filter-flag">
        <option value="">all</option>
        <option value="unreviewed">unreviewed</option>
        <option value="identical">flagged identical</option>
        <option value="different">flagged different</option>
        <option value="borderline">flagged borderline</option>
      </select>
    </label>
  </div>
</header>

<main id="rows"></main>

<div class="export-row">
  <button onclick="exportFlags()">Export my reviews (JSON)</button>
  <button onclick="importFlags()">Import JSON</button>
  <input type="file" id="import-file" style="display:none" accept="application/json" onchange="handleImport(event)">
  <button onclick="clearFlags()" style="color:#e56a6a">Clear all my flags</button>
  <div id="progress"></div>
</div>

<script>
const DATA = {data_json};
const MODE = "{mode}";
const STORAGE_KEY = "visual-equiv-flags-" + MODE;

function loadFlags() {{ try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}"); }} catch(e) {{ return {{}}; }} }}
function saveFlags(f) {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(f)); updateProgress(); }}
let FLAGS = loadFlags();

function flagRow(id, kind) {{
  if (FLAGS[id] && FLAGS[id].kind === kind) {{ delete FLAGS[id]; }}
  else {{ FLAGS[id] = {{ kind, ts: Date.now(), comment: FLAGS[id]?.comment || '' }}; }}
  saveFlags(FLAGS); render();
}}
function commentRow(id, text) {{
  if (!FLAGS[id]) FLAGS[id] = {{ kind: '', ts: Date.now() }};
  FLAGS[id].comment = text;
  saveFlags(FLAGS);
}}

function exportFlags() {{
  const blob = new Blob([JSON.stringify(FLAGS, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'visual-equiv-flags-' + MODE + '-' + new Date().toISOString().slice(0,19).replace(/[:]/g,'-') + '.json';
  a.click();
}}
function importFlags() {{ document.getElementById('import-file').click(); }}
function handleImport(ev) {{
  const f = ev.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = e => {{
    try {{ const imported = JSON.parse(e.target.result); FLAGS = {{...FLAGS, ...imported}}; saveFlags(FLAGS); render(); }}
    catch(err) {{ alert('Import failed: ' + err); }}
  }};
  r.readAsText(f);
}}
function clearFlags() {{
  if (!confirm('Clear all flags for this gallery?')) return;
  FLAGS = {{}}; saveFlags(FLAGS); render();
}}

function updateProgress() {{
  const total = DATA.length;
  const flagged = Object.keys(FLAGS).filter(k => FLAGS[k].kind).length;
  document.getElementById('progress').textContent = `reviewed ${{flagged}}/${{total}}`;
}}

function normalizeMetric(v) {{
  if (v === null || v === undefined || v === '') return NaN;
  const n = parseFloat(v); return isNaN(n) ? NaN : n;
}}

function renderRow(r) {{
  const flag = FLAGS[r.id];
  const flagClass = flag && flag.kind ? ('flagged-' + flag.kind) : '';
  const comment = (flag && flag.comment) || '';
  const ssim = normalizeMetric(r.ssim), mad = normalizeMetric(r.mad), ph = normalizeMetric(r.phash);
  const groupBadge = r.group ? `<span class="badge badge-${{r.group === 'ambiguous' ? 'amb' : r.group}}">{{r.group}}</span>`.replace('{{r.group}}', r.group) : '';
  const title = r.title || r.url || r.id;
  if (MODE === 'ablation') {{
    // 14-up: base + 13 patches
    const shots = r.patches.map(p => {{
      const cls = p.exists ? ('group-' + (p.group === 'ambiguous' ? 'amb' : (p.group || 'err'))) : 'group-err missing';
      const inner = p.exists
        ? `<img src="${{p.src}}" loading="lazy" alt="patch ${{p.patch_id}}"><span class="caption">${{p.patch_id}} · SSIM ${{p.ssim?.toFixed(3) || '?'}}</span>`
        : `<span class="caption">${{p.patch_id}} (missing)</span>`;
      return `<div class="ablation-shot ${{cls}}">${{inner}}</div>`;
    }}).join('');
    return `
      <div class="row ${{flagClass}}" data-id="${{r.id}}">
        <div class="meta">
          <div class="title">${{title}}</div>
          <div class="url">${{r.url || ''}}</div>
          <div class="metric-grid">
            <span class="label">app:</span><span>${{r.app || '?'}}</span>
          </div>
          <div class="flag-buttons">
            <button class="identical ${{flag?.kind === 'identical' ? 'active' : ''}}" onclick="flagRow('${{r.id}}','identical')">✓ OK <span class="hotkey">1</span></button>
            <button class="different ${{flag?.kind === 'different' ? 'active' : ''}}" onclick="flagRow('${{r.id}}','different')">✗ BAD <span class="hotkey">2</span></button>
            <button class="borderline ${{flag?.kind === 'borderline' ? 'active' : ''}}" onclick="flagRow('${{r.id}}','borderline')">? MAYBE <span class="hotkey">3</span></button>
          </div>
          <input class="comment" placeholder="notes…" value="${{comment.replace(/"/g, '&quot;')}}" onchange="commentRow('${{r.id}}', this.value)">
        </div>
        <div class="ablation-grid">${{shots}}</div>
      </div>`;
  }}
  // aggregate 3-up
  const baseShot = r.base_src ? `<img src="${{r.base_src}}" loading="lazy" alt="base">` : '<span>missing</span>';
  const lowShot = r.low_src ? `<img src="${{r.low_src}}" loading="lazy" alt="low">` : '<span>missing</span>';
  const diffShot = r.diff_src ? `<img src="${{r.diff_src}}" loading="lazy" alt="diff">` : '<span>no diff mask</span>';
  return `
    <div class="row ${{flagClass}}" data-id="${{r.id}}">
      <div class="meta">
        <div class="title">${{title}} ${{groupBadge}}</div>
        <div class="url">${{r.url || ''}}</div>
        <div class="metric-grid">
          <span class="label">app:</span><span>${{r.app || '?'}}</span>
          <span class="label">SSIM:</span><span>${{isNaN(ssim) ? '?' : ssim.toFixed(4)}}</span>
          <span class="label">pHash:</span><span>${{isNaN(ph) ? '?' : ph.toFixed(0)}}</span>
          <span class="label">MAD:</span><span>${{isNaN(mad) ? '?' : mad.toFixed(4)}}</span>
          <span class="label">pixels Δ:</span><span>${{r.pct_changed ? (parseFloat(r.pct_changed)*100).toFixed(1) + '%' : '?'}}</span>
          ${{r.visits ? '<span class="label">visits:</span><span>' + r.visits + '</span>' : ''}}
        </div>
        <div class="flag-buttons">
          <button class="identical ${{flag?.kind === 'identical' ? 'active' : ''}}" onclick="flagRow('${{r.id}}','identical')">✓ OK <span class="hotkey">1</span></button>
          <button class="different ${{flag?.kind === 'different' ? 'active' : ''}}" onclick="flagRow('${{r.id}}','different')">✗ BAD <span class="hotkey">2</span></button>
          <button class="borderline ${{flag?.kind === 'borderline' ? 'active' : ''}}" onclick="flagRow('${{r.id}}','borderline')">? MAYBE <span class="hotkey">3</span></button>
        </div>
        <input class="comment" placeholder="notes…" value="${{comment.replace(/"/g, '&quot;')}}" onchange="commentRow('${{r.id}}', this.value)">
      </div>
      <div class="shots">
        <div class="shot"><span class="caption">base</span>${{baseShot}}</div>
        <div class="shot"><span class="caption">low</span>${{lowShot}}</div>
        <div class="shot"><span class="caption">diff</span>${{diffShot}}</div>
      </div>
    </div>`;
}}

function render() {{
  const sort = document.getElementById('sort').value;
  const app = document.getElementById('filter-app').value;
  const group = document.getElementById('filter-group').value;
  const flag = document.getElementById('filter-flag').value;
  let rows = DATA.slice();
  if (app) rows = rows.filter(r => r.app === app);
  if (group) rows = rows.filter(r => r.group === group);
  if (flag) {{
    if (flag === 'unreviewed') rows = rows.filter(r => !FLAGS[r.id] || !FLAGS[r.id].kind);
    else rows = rows.filter(r => FLAGS[r.id] && FLAGS[r.id].kind === flag);
  }}
  rows.sort((a, b) => {{
    switch (sort) {{
      case 'ssim_asc': return (normalizeMetric(a.ssim) || 1) - (normalizeMetric(b.ssim) || 1);
      case 'ssim_desc': return (normalizeMetric(b.ssim) || 0) - (normalizeMetric(a.ssim) || 0);
      case 'app': return (a.app || '').localeCompare(b.app || '');
      case 'group': return (a.group || '').localeCompare(b.group || '');
      default: return (a.url || '').localeCompare(b.url || '');
    }}
  }});
  document.getElementById('rows').innerHTML = rows.map(renderRow).join('');
  document.getElementById('stats').innerHTML =
    `<strong>${{rows.length}}</strong> rows / ${{DATA.length}} total`;
  updateProgress();
}}

// Keyboard shortcuts: 1/2/3 flag, J/K navigate
document.addEventListener('keydown', e => {{
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
  const focused = document.querySelector('.row:hover') || document.querySelector('.row');
  if (!focused) return;
  const id = focused.getAttribute('data-id');
  if (e.key === '1') {{ flagRow(id, 'identical'); e.preventDefault(); }}
  else if (e.key === '2') {{ flagRow(id, 'different'); e.preventDefault(); }}
  else if (e.key === '3') {{ flagRow(id, 'borderline'); e.preventDefault(); }}
  else if (e.key === 'j') {{ focused.nextElementSibling?.scrollIntoView({{block:'start'}}); e.preventDefault(); }}
  else if (e.key === 'k') {{ focused.previousElementSibling?.scrollIntoView({{block:'start'}}); e.preventDefault(); }}
}});

// Populate app filter
const apps = [...new Set(DATA.map(r => r.app).filter(Boolean))].sort();
for (const a of apps) {{
  const opt = document.createElement('option'); opt.value = opt.textContent = a;
  document.getElementById('filter-app').appendChild(opt);
}}

['sort', 'filter-app', 'filter-group', 'filter-flag'].forEach(id =>
  document.getElementById(id).addEventListener('change', render));
render();
</script>
"""


def load_aggregate_metrics(csv_path: pathlib.Path, screenshots_root: pathlib.Path,
                            embed_base64: bool = False) -> list[dict]:
    """Build gallery rows from aggregate metrics CSV + screenshot directory."""
    rows = []
    if not csv_path.exists():
        print(f"WARN: metrics CSV not found at {csv_path} — using raw manifest instead", file=sys.stderr)
        # Fall back to manifest
        manifest = screenshots_root / "manifest.json"
        if not manifest.exists():
            return rows
        with manifest.open(encoding="utf-8") as f:
            m = json.load(f)
        # Build pairs from records grouped by URL
        by_url: dict[str, dict] = {}
        for rec in m.get("records", []):
            if not rec.get("success"):
                continue
            url = rec.get("url")
            variant = rec.get("variant")
            shot = rec.get("screenshot")
            slug = rec.get("slug")
            if not url or not variant or not shot:
                continue
            by_url.setdefault(url, {"url": url, "slug": slug,
                                    "app": rec.get("app", ""),
                                    "visits": rec.get("visits", "")})
            by_url[url][variant + "_src"] = _img_src(shot, embed_base64)
        for idx, (url, d) in enumerate(by_url.items()):
            d["id"] = f"row-{idx}"
            d["title"] = d.get("slug", url)
            rows.append(d)
        return rows
    # Use the per-pair metrics CSV (has SSIM/pHash/MAD/group)
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            tid = row.get("task_id", "")
            rep = row.get("rep", "")
            rid = row.get("case_id", "") or f"{tid}-{rep}"
            row_out = {
                "id": f"row-{idx}",
                "task_id": tid,
                "rep": rep,
                "app": row.get("app", ""),
                "url": row.get("url", ""),
                "title": row.get("title", "") or f"task {tid} rep {rep}",
                "ssim": row.get("ssim", ""),
                "mad": row.get("mad", ""),
                "phash": row.get("phash_distance", ""),
                "pct_changed": row.get("pct_changed", ""),
                "group": row.get("group", ""),
                "base_src": "",
                "low_src": "",
                "diff_src": "",
            }
            # Resolve screenshot paths by convention
            base_p = row.get("base_path", "")
            var_p = row.get("variant_path", "")
            if base_p:
                row_out["base_src"] = _img_src(base_p, embed_base64)
            if var_p:
                row_out["low_src"] = _img_src(var_p, embed_base64)
            # Diff mask: analysis saves under diff_masks/
            diff_candidate = screenshots_root.parent / "diff_masks" / f"task_{tid}_r{rep}.png"
            if diff_candidate.exists():
                row_out["diff_src"] = _img_src(str(diff_candidate), embed_base64)
            rows.append(row_out)
    return rows


def load_ablation_metrics(csv_path: pathlib.Path, screenshots_root: pathlib.Path,
                           embed_base64: bool = False) -> list[dict]:
    """Build 14-up ablation gallery rows."""
    rows: dict[str, dict] = {}
    # Track base images by task so every task-row gets its base thumbnail
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = row.get("task_id", "")
            pid_raw = row.get("patch_id", "0")
            try:
                pid = int(pid_raw)
            except ValueError:
                pid = 0
            base_p = row.get("base_path", "")
            var_p = row.get("variant_path", "")
            entry = rows.setdefault(tid, {
                "id": f"row-{tid}", "task_id": tid,
                "url": "", "title": f"task {tid}",
                "app": "", "patches": [], "base_src": "",
            })
            if pid == 0:
                entry["base_src"] = _img_src(base_p, embed_base64) if base_p else ""
            patch_entry = {
                "patch_id": pid,
                "patch_name": row.get("patch_name", ""),
                "ssim": float(row.get("ssim", "0") or 0) or None,
                "mad": float(row.get("mad", "0") or 0) or None,
                "phash": row.get("phash_distance", ""),
                "group": row.get("group", ""),
                "src": _img_src(var_p, embed_base64) if var_p else "",
                "exists": bool(var_p),
            }
            entry["patches"].append(patch_entry)
    # Sort patches per task
    out = []
    for tid in sorted(rows.keys()):
        entry = rows[tid]
        entry["patches"].sort(key=lambda p: p["patch_id"])
        out.append(entry)
    return out


def _img_src(path: str, embed_base64: bool) -> str:
    """Return an HTML src string for an image file — either file:// reference
    or data URI (embed_base64)."""
    if not path:
        return ""
    p = pathlib.Path(path)
    if not p.exists():
        return ""
    if embed_base64:
        data = p.read_bytes()
        return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"
    # Use forward slashes for HTML regardless of OS
    return p.resolve().as_posix()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["aggregate", "ablation"], required=True)
    ap.add_argument("--metrics", required=True,
                    help="CSV output from visual_equivalence_analysis.py")
    ap.add_argument("--screenshots",
                    help="Root dir containing per-URL screenshot subfolders "
                         "(used as fallback if metrics CSV paths missing)")
    ap.add_argument("--output", default="results/visual-equivalence/gallery.html")
    ap.add_argument("--embed-base64", action="store_true",
                    help="Inline all screenshots as base64 data URIs (large HTML, "
                         "but self-contained for sharing)")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    csv_path = pathlib.Path(args.metrics)
    if not csv_path.exists():
        print(f"ERROR: metrics CSV not found at {csv_path}", file=sys.stderr)
        print(f"  Run: python3 analysis/visual_equivalence_analysis.py --mode {args.mode} "
              f"--input <screenshot_dir> --output <results_dir>", file=sys.stderr)
        sys.exit(1)

    screenshots_root = pathlib.Path(args.screenshots) if args.screenshots else csv_path.parent

    if args.mode == "aggregate":
        rows = load_aggregate_metrics(csv_path, screenshots_root, args.embed_base64)
    else:
        rows = load_ablation_metrics(csv_path, screenshots_root, args.embed_base64)

    title = args.title or f"Visual Equivalence — {args.mode.title()}"
    html = HTML_TEMPLATE.format(
        title=title,
        mode=args.mode,
        data_json=json.dumps(rows, ensure_ascii=False),
    )

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({size_kb:.1f} KB, {len(rows)} rows)", file=sys.stderr)
    print(f"Open in browser: file:///{out_path.resolve().as_posix()}", file=sys.stderr)
    print(f"Keyboard: 1=identical, 2=different, 3=borderline, J/K=navigate", file=sys.stderr)


if __name__ == "__main__":
    main()
