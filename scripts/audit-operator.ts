#!/usr/bin/env tsx
/**
 * audit-operator.ts — compute the 12-dimensional DOM signature for
 * each AMT operator on a given URL.
 *
 * For each operator in the canonical list, we:
 *   1. Open the URL in a fresh Playwright context (full reset).
 *   2. Capture the BEFORE state: DOM metrics, a11y snapshot, screenshot,
 *      bounding boxes, focusable set, contrast samples.
 *   3. Inject the operator (via apply-all-individual.js with a single-ID
 *      __OPERATOR_IDS).
 *   4. Capture the AFTER state.
 *   5. Compute per-dimension deltas.
 *
 * We also capture a single base-only run once per URL so multiple
 * operator audits share the same BEFORE snapshot (faster, lower
 * variance). For Plan D correctness this is safe because operators
 * start from a pristine DOM — the BEFORE doesn't drift.
 *
 * SSIM (V1) is computed via a Python helper (analysis/requirements.txt
 * already has scikit-image). Node has no first-class SSIM.
 *
 * Usage:
 *   npx tsx scripts/audit-operator.ts \
 *     --url http://10.0.1.50:7770/ \
 *     --operators L1,L2,H4 \
 *     --output results/amt/dom-signatures/shopping-home.json
 *
 *   # All 26 operators:
 *   npx tsx scripts/audit-operator.ts --url ... --output ...
 *
 * Spec: docs/amt-operator-spec.md §2.4 + roadmap v8 §2.4 + Task A.5.
 */
import { chromium } from 'playwright';
import type { Browser, BrowserContext, Page } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..');
const APPLY_ALL = join(REPO, 'src/variants/patches/inject/apply-all-individual.js');
const SSIM_HELPER = join(REPO, 'analysis/ssim_helper.py');
const LOGIN_HELPER = join(REPO, 'scripts/webarena_login.py');

// Canonical order — keep in sync with build-operators.ts and spec §8.4.
const OPERATOR_ORDER: readonly string[] = [
  'H1', 'H2', 'H3', 'H4', 'H5a', 'H5b', 'H5c', 'H6', 'H7', 'H8',
  'ML1', 'ML2', 'ML3',
  'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9',
  'L10', 'L11', 'L12', 'L13',
] as const;

// ─────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────

interface PageMetrics {
  /** Count of elements by tagName (lower-cased). */
  tagCounts: Record<string, number>;
  /** Total element count in the document. */
  nodeCount: number;
  /** Map of "tag:attr" → count (how many elements of that tag carry attr). */
  attrPresence: Record<string, number>;
  /** Count of elements with non-empty inline event handlers. */
  inlineHandlerCount: number;
  /** Count of elements matching a broad "interactive" selector. */
  interactiveCount: number;
  /** Count of elements with tabIndex ≥ 0 (focusable). */
  focusableCount: number;
  /** Accessibility tree snapshot flattened to role+name pairs. */
  a11yNodes: Array<{ role: string; name: string }>;
  /** ARIA state summary. */
  ariaStates: Record<string, number>;
  /** Bounding boxes of first N interactive elements — for V2. */
  interactiveBBoxes: Array<{ tag: string; x: number; y: number; w: number; h: number }>;
  /** Contrast ratios sampled from interactive text elements — for V3. */
  contrastSamples: Array<{ tag: string; ratio: number }>;
  /** Path to the full-page screenshot PNG on disk. */
  screenshotPath: string;
}

interface OperatorSignature {
  // DOM (D1-D3)
  D1_tagCountDeltas: Record<string, number>;      // signed delta per tag
  D2_attrChanges: { added: number; removed: number };
  D3_nodeCountDelta: number;
  // A11y (A1-A3)
  A1_rolesChanged: number;                        // count of (before_role → after_role) mismatches by index
  A2_namesChanged: number;
  A3_ariaStateChanges: Record<string, number>;
  // Visual (V1-V3)
  V1_ssim: number | null;                         // 0..1; 1 = identical
  V2_maxBBoxShift_px: number;                     // max Euclidean shift across matched interactives
  V3_meanContrastDelta: number;                   // mean |after - before| over sampled elements
  // Functional (F1-F3)
  F1_interactiveCountDelta: number;
  F2_inlineHandlerDelta: number;
  F3_focusableCountDelta: number;
  // Diagnostic
  changesReturned: number;                        // how many Change records the operator produced
  durationMs: number;
}

// ─────────────────────────────────────────────────────────────────────
// Page-side measurement — runs in the browser via page.evaluate
// ─────────────────────────────────────────────────────────────────────

/**
 * Collects every DOM/a11y/functional metric we need from inside the page.
 * Returns a single object; Playwright serializes it back to Node.
 *
 * V1 (screenshot SSIM) and V2 (bbox) are computed outside this function
 * because SSIM needs Python and bbox needs matching pre/post elements
 * which we do at the Node layer.
 */
const PAGE_METRICS_JS = `(() => {
  const tagCounts = {};
  const attrPresence = {};
  let nodeCount = 0;
  let inlineHandlerCount = 0;
  const inlineHandlerAttrs = ['onclick','onkeydown','onkeyup','onkeypress','onfocus','onblur','onchange','onsubmit'];

  for (const el of document.querySelectorAll('*')) {
    nodeCount++;
    const tag = el.tagName.toLowerCase();
    tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    for (const attr of el.attributes) {
      const key = tag + ':' + attr.name;
      attrPresence[key] = (attrPresence[key] || 0) + 1;
    }
    for (const h of inlineHandlerAttrs) {
      if (el.hasAttribute(h)) { inlineHandlerCount++; break; }
    }
  }

  const interactiveSel = 'button, a[href], input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="tab"], [role="menuitem"]';
  const interactives = Array.from(document.querySelectorAll(interactiveSel));
  const interactiveCount = interactives.length;

  let focusableCount = 0;
  for (const el of document.querySelectorAll('*')) {
    const ti = el.tabIndex;
    if (typeof ti === 'number' && ti >= 0) focusableCount++;
  }

  // ARIA states — count elements bearing each known state attribute
  const stateAttrs = ['aria-expanded','aria-checked','aria-pressed','aria-disabled','aria-selected','aria-hidden','aria-current','aria-required','aria-invalid'];
  const ariaStates = {};
  for (const attr of stateAttrs) {
    ariaStates[attr] = document.querySelectorAll('[' + attr + ']').length;
  }

  // BBoxes of first 50 interactives — enough signal for V2 without blowup
  const interactiveBBoxes = [];
  for (let i = 0; i < Math.min(interactives.length, 50); i++) {
    const el = interactives[i];
    const r = el.getBoundingClientRect();
    interactiveBBoxes.push({
      tag: el.tagName.toLowerCase(),
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
    });
  }

  // Contrast samples on interactive text elements (first 20)
  function parseRgb(s) {
    const m = /rgba?\\(([^)]+)\\)/.exec(s);
    if (!m) return null;
    const parts = m[1].split(',').map(x => parseFloat(x.trim()));
    return parts.slice(0, 3);
  }
  function luminance([r, g, b]) {
    const ch = [r, g, b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  }
  function contrastRatio(fg, bg) {
    if (!fg || !bg) return 1;
    const lf = luminance(fg), lb = luminance(bg);
    const hi = Math.max(lf, lb), lo = Math.min(lf, lb);
    return (hi + 0.05) / (lo + 0.05);
  }
  const contrastSamples = [];
  for (let i = 0; i < Math.min(interactives.length, 20); i++) {
    const el = interactives[i];
    const cs = getComputedStyle(el);
    const fg = parseRgb(cs.color);
    // Walk up for effective background (most elements have rgba(0,0,0,0))
    let node = el, bg = null;
    while (node && !bg) {
      const bgStr = getComputedStyle(node).backgroundColor;
      const parsed = parseRgb(bgStr);
      if (parsed && bgStr !== 'rgba(0, 0, 0, 0)' && bgStr !== 'transparent') bg = parsed;
      node = node.parentElement;
    }
    if (!bg) bg = [255, 255, 255]; // default to white
    contrastSamples.push({ tag: el.tagName.toLowerCase(), ratio: Number(contrastRatio(fg, bg).toFixed(2)) });
  }

  return {
    tagCounts, nodeCount, attrPresence, inlineHandlerCount,
    interactiveCount, focusableCount, ariaStates,
    interactiveBBoxes, contrastSamples,
  };
})()`;

// ─────────────────────────────────────────────────────────────────────
// A11y snapshot via Playwright
// ─────────────────────────────────────────────────────────────────────

/**
 * Flatten a CDP accessibility tree into a stable list of {role, name}
 * pairs in DOM pre-order. Two lists can be compared by multiset diff
 * (see a11yTreeDeltas) to detect role/name changes.
 *
 * We go through CDP directly because Playwright 1.59+ removed the
 * `page.accessibility.snapshot()` convenience. CDP's Accessibility
 * domain is marked Experimental but is the same data source Chromium
 * uses for `interestingOnly=true` snapshots; we request the full tree.
 */
async function flattenA11yTree(page: Page): Promise<Array<{ role: string; name: string }>> {
  const cdp = await page.context().newCDPSession(page);
  try {
    await cdp.send('Accessibility.enable');
    const { nodes } = await cdp.send('Accessibility.getFullAXTree') as {
      nodes: Array<{
        role?: { value?: string };
        name?: { value?: string };
        ignored?: boolean;
      }>;
    };
    const out: Array<{ role: string; name: string }> = [];
    for (const n of nodes) {
      if (n.ignored) continue;
      const role = n.role?.value ?? '';
      const name = n.name?.value ?? '';
      if (!role && !name) continue;
      out.push({ role, name });
    }
    return out;
  } catch {
    return [];
  } finally {
    try { await cdp.detach(); } catch { /* noop */ }
  }
}

// ─────────────────────────────────────────────────────────────────────
// Screenshot + SSIM helper
// ─────────────────────────────────────────────────────────────────────

/**
 * Compute SSIM between two PNG files by shelling out to a Python
 * helper (scikit-image). Returns null on any failure.
 *
 * Returns a float in [0, 1]; 1.0 means pixel-identical.
 */
function computeSSIM(beforePath: string, afterPath: string): number | null {
  const res = spawnSync('python3', [SSIM_HELPER, beforePath, afterPath], {
    encoding: 'utf-8',
    timeout: 20_000,
  });
  if (res.status !== 0) {
    process.stderr.write(`[audit] SSIM helper failed: ${res.stderr?.slice(0, 200)}\n`);
    return null;
  }
  const n = parseFloat(res.stdout.trim());
  return Number.isFinite(n) ? n : null;
}

/**
 * Cookie shape accepted by Playwright's `context.addCookies()`.
 * Mirrors the JSON emitted by `scripts/webarena_login.py`.
 */
interface LoginCookie {
  name: string;
  value: string;
  domain: string;
  path: string;
}

/**
 * Spawn scripts/webarena_login.py to authenticate to a WebArena app
 * and return the resulting cookies. Returns null on any failure —
 * caller decides whether to proceed anonymously (for public URLs) or
 * abort (for URLs known to require auth).
 *
 * We prefer python3.11 if present (ssm-bootstrap-platform.json installs
 * it on EC2; Homebrew installs it on dev Macs). Falls back to python3.
 * The login helper uses `from __future__ import annotations` so 3.9+
 * works, but 3.11 is our documented supported floor.
 */
function fetchLoginCookies(app: string, baseUrl: string): LoginCookie[] | null {
  // Resolve the Python interpreter: prefer 3.11, else fall back to python3.
  const pyCandidates = ['python3.11', 'python3'];
  let chosenPy: string | null = null;
  for (const cand of pyCandidates) {
    const probe = spawnSync(cand, ['--version'], { encoding: 'utf-8' });
    if (probe.status === 0) { chosenPy = cand; break; }
  }
  if (chosenPy === null) {
    process.stderr.write('[audit] no usable python3 interpreter on PATH\n');
    return null;
  }

  const res = spawnSync(
    chosenPy,
    [LOGIN_HELPER, '--app', app, '--base-url', baseUrl],
    { encoding: 'utf-8', timeout: 60_000 },
  );
  // Login helper prints diagnostics to stderr; surface a single trailing
  // line so the audit log includes "captured N cookies" context.
  const stderrTail = (res.stderr ?? '').trim().split('\n').slice(-3).join(' | ');
  if (stderrTail) {
    process.stderr.write(`[audit] login(${app}): ${stderrTail.slice(0, 400)}\n`);
  }
  if (res.status !== 0 && res.status !== null) {
    // exit code 1 = login had 0 cookies (still printed JSON — parse anyway);
    // exit code 2 = argparse error (don't try to parse); other = fatal.
    if (res.status !== 1) {
      process.stderr.write(
        `[audit] webarena_login.py exited ${res.status}. stdout: ${(res.stdout ?? '').slice(0, 200)}\n`,
      );
      return null;
    }
  }
  try {
    const parsed = JSON.parse(res.stdout || '{}');
    const cookies = Array.isArray(parsed.cookies) ? parsed.cookies : [];
    if (!parsed.ok || cookies.length === 0) {
      process.stderr.write(
        `[audit] login(${app}): 0 cookies (ok=${parsed.ok})\n`,
      );
      return null;
    }
    return cookies as LoginCookie[];
  } catch (e) {
    process.stderr.write(
      `[audit] could not parse webarena_login.py stdout: ${String(e).slice(0, 200)}\n`,
    );
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Delta computation — pure Node-side
// ─────────────────────────────────────────────────────────────────────

/**
 * D1: signed delta of tag counts. Positive means tag appears more after.
 * Omits tags whose count is unchanged.
 */
function tagCountDeltas(before: Record<string, number>, after: Record<string, number>): Record<string, number> {
  const delta: Record<string, number> = {};
  const tags = new Set([...Object.keys(before), ...Object.keys(after)]);
  for (const t of tags) {
    const d = (after[t] ?? 0) - (before[t] ?? 0);
    if (d !== 0) delta[t] = d;
  }
  return delta;
}

/**
 * D2: attributes added vs removed across all (tag, attr) pairs.
 * This is symmetric — "moving" an attribute counts as remove+add.
 */
function attrChangeCounts(
  before: Record<string, number>,
  after: Record<string, number>,
): { added: number; removed: number } {
  let added = 0, removed = 0;
  const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
  for (const k of keys) {
    const d = (after[k] ?? 0) - (before[k] ?? 0);
    if (d > 0) added += d;
    else if (d < 0) removed += -d;
  }
  return { added, removed };
}

/**
 * A1 + A2: a11y tree deltas computed as multiset symmetric difference,
 * not index-pair diff. Index-pair would miss node removals (everything
 * just shifts up). We count:
 *   A1 (rolesChanged) = (roles only in before) + (roles only in after)
 *                       measured at the role-bag level
 *   A2 (namesChanged) = same for {role, name} pairs (tightening the key)
 */
function a11yTreeDeltas(
  before: Array<{ role: string; name: string }>,
  after: Array<{ role: string; name: string }>,
): { rolesChanged: number; namesChanged: number } {
  function bag<K extends string>(items: K[]): Map<K, number> {
    const m = new Map<K, number>();
    for (const k of items) m.set(k, (m.get(k) ?? 0) + 1);
    return m;
  }
  function symDiff(a: Map<string, number>, b: Map<string, number>): number {
    const keys = new Set([...a.keys(), ...b.keys()]);
    let diff = 0;
    for (const k of keys) diff += Math.abs((a.get(k) ?? 0) - (b.get(k) ?? 0));
    return diff;
  }
  const roleBagB = bag(before.map(n => n.role));
  const roleBagA = bag(after.map(n => n.role));
  const rolesChanged = symDiff(roleBagB, roleBagA);

  const pairBagB = bag(before.map(n => `${n.role}\u0000${n.name}`));
  const pairBagA = bag(after.map(n => `${n.role}\u0000${n.name}`));
  const namesChanged = symDiff(pairBagB, pairBagA);

  return { rolesChanged, namesChanged };
}

/**
 * A3: ARIA state attribute presence delta. Returns the per-attr signed
 * delta for the states we track.
 */
function ariaStateDeltas(
  before: Record<string, number>,
  after: Record<string, number>,
): Record<string, number> {
  const out: Record<string, number> = {};
  const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
  for (const k of keys) {
    const d = (after[k] ?? 0) - (before[k] ?? 0);
    if (d !== 0) out[k] = d;
  }
  return out;
}

/**
 * V2: max Euclidean shift of matched interactive bboxes. Pairs by
 * position in the list (same index before/after). Mismatched lengths:
 * we only match up to the shorter list (the extra items are reported
 * via F1 interactiveCountDelta).
 */
function maxBBoxShift(
  before: Array<{ x: number; y: number; w: number; h: number }>,
  after: Array<{ x: number; y: number; w: number; h: number }>,
): number {
  let max = 0;
  const len = Math.min(before.length, after.length);
  for (let i = 0; i < len; i++) {
    const dx = after[i].x - before[i].x;
    const dy = after[i].y - before[i].y;
    const d = Math.sqrt(dx * dx + dy * dy);
    if (d > max) max = d;
  }
  return Math.round(max);
}

/**
 * V3: mean |after - before| contrast ratio over matched samples.
 */
function meanContrastDelta(
  before: Array<{ ratio: number }>,
  after: Array<{ ratio: number }>,
): number {
  const len = Math.min(before.length, after.length);
  if (len === 0) return 0;
  let sum = 0;
  for (let i = 0; i < len; i++) sum += Math.abs(after[i].ratio - before[i].ratio);
  return Number((sum / len).toFixed(3));
}

// ─────────────────────────────────────────────────────────────────────
// Main measurement flow per operator
// ─────────────────────────────────────────────────────────────────────

/**
 * Open `url` in a fresh context and capture a BEFORE metrics snapshot.
 * If `operatorId` is provided, inject that operator and capture AFTER
 * as well, then close and return both sets.
 *
 * Screenshots are written to `screenshotDir` and referenced in the
 * metrics (paths are absolute).
 */
async function captureOperatorPair(
  browser: Browser,
  url: string,
  operatorId: string | null,
  screenshotDir: string,
  label: string, // e.g. "base" or "L3"
  settleMs: number,
  applyAllJs: string,
  loginCookies: LoginCookie[] | null,
): Promise<{ before: PageMetrics; after: PageMetrics | null }> {
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  if (loginCookies && loginCookies.length > 0) {
    await context.addCookies(loginCookies);
  }
  const page = await context.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    try {
      await page.waitForLoadState('networkidle', { timeout: 10_000 });
    } catch { /* tolerated */ }
    await page.waitForTimeout(settleMs);

    const beforeRaw: any = await page.evaluate(PAGE_METRICS_JS);
    const beforeA11y = await flattenA11yTree(page);
    const beforeShot = join(screenshotDir, `${label}_before.png`);
    await page.screenshot({ path: beforeShot, fullPage: false });

    const before: PageMetrics = {
      ...beforeRaw,
      a11yNodes: beforeA11y,
      screenshotPath: beforeShot,
    };

    if (!operatorId) {
      return { before, after: null };
    }

    // Inject single operator
    await page.evaluate(`window.__OPERATOR_IDS = ${JSON.stringify([operatorId])}; window.__OPERATOR_STRICT = true;`);
    const changes = (await page.evaluate(applyAllJs)) as Array<any>;
    await page.waitForTimeout(300); // let layout settle

    const afterRaw: any = await page.evaluate(PAGE_METRICS_JS);
    const afterA11y = await flattenA11yTree(page);
    const afterShot = join(screenshotDir, `${label}_after.png`);
    await page.screenshot({ path: afterShot, fullPage: false });

    const after: PageMetrics = {
      ...afterRaw,
      a11yNodes: afterA11y,
      screenshotPath: afterShot,
    };
    (after as any).__changes = changes.length;

    return { before, after };
  } finally {
    await context.close();
  }
}

function deriveSignature(
  before: PageMetrics,
  after: PageMetrics,
  changesReturned: number,
  durationMs: number,
): OperatorSignature {
  const ssim = computeSSIM(before.screenshotPath, after.screenshotPath);
  return {
    D1_tagCountDeltas: tagCountDeltas(before.tagCounts, after.tagCounts),
    D2_attrChanges: attrChangeCounts(before.attrPresence, after.attrPresence),
    D3_nodeCountDelta: after.nodeCount - before.nodeCount,
    ...(() => {
      const { rolesChanged, namesChanged } = a11yTreeDeltas(before.a11yNodes, after.a11yNodes);
      return { A1_rolesChanged: rolesChanged, A2_namesChanged: namesChanged };
    })(),
    A3_ariaStateChanges: ariaStateDeltas(before.ariaStates, after.ariaStates),
    V1_ssim: ssim,
    V2_maxBBoxShift_px: maxBBoxShift(before.interactiveBBoxes, after.interactiveBBoxes),
    V3_meanContrastDelta: meanContrastDelta(before.contrastSamples, after.contrastSamples),
    F1_interactiveCountDelta: after.interactiveCount - before.interactiveCount,
    F2_inlineHandlerDelta: after.inlineHandlerCount - before.inlineHandlerCount,
    F3_focusableCountDelta: after.focusableCount - before.focusableCount,
    changesReturned,
    durationMs,
  };
}

// ─────────────────────────────────────────────────────────────────────
// CLI + main
// ─────────────────────────────────────────────────────────────────────

function parseArgs(argv: string[]): Record<string, string> {
  const args: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : 'true';
      args[key] = val;
    }
  }
  return args;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const url = args['url'];
  if (!url) {
    console.error('Usage: audit-operator.ts --url <url> [--operators L1,H2,...] [--output path.json] [--settle-ms 1500] [--login-app shopping|shopping_admin|reddit|gitlab] [--login-base-url URL]');
    process.exit(2);
  }
  const outputPath = args['output'] || join(REPO, 'results/amt/dom-signatures/audit.json');
  const opsArg = args['operators'];
  const operators = opsArg ? opsArg.split(',').map(s => s.trim()).filter(Boolean) : [...OPERATOR_ORDER];
  const settleMs = parseInt(args['settle-ms'] || '1500', 10);
  const loginApp = args['login-app'] || '';
  // If login-base-url isn't specified, derive from the target URL's
  // scheme://host:port — this is the common case where we're auditing
  // a single WebArena app.
  const loginBaseUrl = args['login-base-url'] || (() => {
    try {
      const u = new URL(url);
      return loginApp ? `${u.protocol}//${u.host}` : '';
    } catch { return ''; }
  })();

  // Validate operator IDs
  const validSet = new Set(OPERATOR_ORDER);
  for (const id of operators) {
    if (!validSet.has(id)) {
      console.error(`[audit] Unknown operator id: ${id}`);
      process.exit(2);
    }
  }

  // Fetch login cookies if requested — done ONCE before the operator
  // loop, cookies are reused for all 26 operator contexts. If login
  // fails, we abort rather than silently audit the login page.
  let loginCookies: LoginCookie[] | null = null;
  if (loginApp) {
    if (!loginBaseUrl) {
      console.error('[audit] --login-app specified but --login-base-url could not be derived from --url; pass --login-base-url explicitly');
      process.exit(2);
    }
    console.error(`[audit] Authenticating: app=${loginApp} base=${loginBaseUrl}`);
    loginCookies = fetchLoginCookies(loginApp, loginBaseUrl);
    if (!loginCookies || loginCookies.length === 0) {
      console.error('[audit] login failed — aborting. Use no --login-app for anonymous audits.');
      process.exit(3);
    }
    console.error(`[audit] login: ${loginCookies.length} cookies`);
  }

  // Load the built artefact — fail fast if stale
  const applyAllJs = readFileSync(APPLY_ALL, 'utf-8');

  const screenshotDir = join(tmpdir(), `amt-audit-${Date.now()}`);
  mkdirSync(screenshotDir, { recursive: true });

  mkdirSync(dirname(outputPath), { recursive: true });

  console.error(`[audit] URL:        ${url}`);
  console.error(`[audit] Operators:  ${operators.length} (${operators.slice(0, 6).join(',')}${operators.length > 6 ? ',…' : ''})`);
  console.error(`[audit] Output:     ${outputPath}`);
  console.error(`[audit] Screenshots: ${screenshotDir}`);

  const browser = await chromium.launch({ headless: true });
  const signatures: Record<string, OperatorSignature> = {};
  const errors: Record<string, string> = {};

  const t0 = Date.now();
  try {
    for (let i = 0; i < operators.length; i++) {
      const opId = operators[i];
      const opT0 = Date.now();
      try {
        const { before, after } = await captureOperatorPair(
          browser, url, opId, screenshotDir, opId, settleMs, applyAllJs, loginCookies,
        );
        if (!after) throw new Error('after metrics missing');
        const changesReturned = (after as any).__changes ?? 0;
        signatures[opId] = deriveSignature(before, after, changesReturned, Date.now() - opT0);
        console.error(`[audit] [${i + 1}/${operators.length}] ${opId} — ${signatures[opId].changesReturned} changes, ssim=${signatures[opId].V1_ssim}, bbox=${signatures[opId].V2_maxBBoxShift_px}px, ${Date.now() - opT0}ms`);
      } catch (e: any) {
        errors[opId] = String(e?.message || e);
        console.error(`[audit] [${i + 1}/${operators.length}] ${opId} — FAILED: ${errors[opId]}`);
      }
    }
  } finally {
    await browser.close();
  }

  const output = {
    schemaVersion: 'amt-dom-signature/v1',
    timestamp: new Date().toISOString(),
    fixture: {
      url,
      loginApp: loginApp || null,
      loginBaseUrl: loginApp ? loginBaseUrl : null,
      authenticated: !!loginCookies,
    },
    settleMs,
    operators: signatures,
    errors,
    totalDurationMs: Date.now() - t0,
  };
  writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.error(`[audit] Done in ${Math.round((Date.now() - t0) / 1000)}s. Wrote ${outputPath}`);
  if (Object.keys(errors).length > 0) process.exit(1);
}

main().catch(e => { console.error(e); process.exit(1); });
