# Visual Equivalence Validation — Experiment Plan (v2 — URL Replay)

**Date**: 2026-04-22 (v2)
**Status**: Scripts ready. Deployment on new burner (840744349421) in progress.

## What changed from v1

v1 plan: run `env.reset()` for each of 13 tasks, let the bridge do login + Plan D
injection, screenshot the first-observation page. Captures ONLY the task start
page (26 screenshots total).

v2 plan: **URL replay**. Extract every unique URL the agents actually visited
across all 3,379 historical cases (137 unique URLs), then render each URL under
`base` and `low` variants directly via Playwright (no BrowserGym, no agent loop),
inject `apply-low.js`, screenshot, pixel-compare. Captures what agents ACTUALLY
saw, not just start pages.

**Why v2 is stronger**:
- Broader ecological coverage: 137 pages vs 26 start pages
- Higher statistical power: more pairs → tighter SSIM confidence intervals
- Cleaner pipeline: Playwright only, no BrowserGym state dependency
- Matches Ma11y (ISSTA 2024) methodology: static-site mutation replay

**Why v2 is legitimate**: the claim being tested is purely about **rendering
equivalence** of `apply-low.js` patches — it is deterministic with respect to
{ URL, viewport, login cookies, patch script }. The agent's presence is
irrelevant to whether the pixels are equivalent; what matters is whether the
agent *saw equivalent pixels*, which URL-replay directly answers by rendering
the pages the agent actually visited.

## Design

### Part A — Extract agent URLs (DONE)

Walks every trace on disk, emits one row per (case, step, url, action).

- Script: `scripts/extract_agent_urls.py`
- Output: `results/visual-equivalence/agent-urls{.csv,-dedup.csv,-summary.md}`
- Result (2026-04-22):
  - 3,379 cases scanned
  - 137 unique URLs (136 replayable — 1 excluded as chrome-error/about:blank)
  - 76 ecommerce_admin + 32 reddit + 23 gitlab + 6 ecommerce

Top-visited URLs match task semantics: admin order listing, product pages,
forum pages (f/books), commit browsers (primer/design/-/graphs/main), search
pages. The URL set spans all 13 tasks × 4 variants.

### Part B — URL Replay Screenshots (EC2)

Script: `scripts/replay-url-screenshots.py`

For each replayable URL × {base, low}:
1. Launch Playwright chromium at **1280×720 viewport** (matches BrowserGym default)
2. Set WebArena app login cookies (admin/admin, emma.lopez/Password.123)
3. Navigate to URL, wait for `networkidle` + 1500ms settle
4. If variant="low": `page.evaluate(apply-low.js)`; wait for layout reflow
5. `page.screenshot(full_page=False)` → PNG
6. Record viewport, URL (in case of redirects), title, HTML size, load duration

Variants: `base`, `low` (can extend to `medium-low`, `high` if we want the full
matrix; but `base` vs `low` is the only comparison that matters for §6
Limitations decomposition).

IP rewriting: historical traces use both `10.0.1.49` (old burner) and
`10.0.1.50` (recent burner). The replay script rewrites both to the current
WebArena IP before navigating.

### Part C — Per-patch ablation on a representative URL set

Script: `scripts/replay-url-patch-ablation.py` (thin driver on top of Part B)

For ONE representative URL per app (4 total), apply each of 13 patches
individually via `apply-low-individual.js` (`window.__ONLY_PATCH_ID = N`),
screenshot, compare to base.

Representative URLs:
- ecommerce: `/epson-workforce-wf-3620-...` (product page — nav, header, img, reviews)
- ecommerce_admin: `/admin/sales/order/` (admin grid — tables, filters, landmarks)
- reddit: `/f/books` (forum listing — many links, headings)
- gitlab: `/primer/design/-/graphs/main` (svg chart + sidebar + tables)

4 × 13 = 52 ablation screenshots + 4 base refs.

### Part D — Analysis (local, SSIM / pHash / MAD)

Script: `analysis/visual_equivalence_analysis.py` (already written, works)

Two modes:
- `--mode aggregate` consumes Part B output → per-URL base-vs-low metrics
- `--mode ablation` consumes Part C output → per-patch Group A/B/C classification

Thresholds:
- Group A: SSIM ≥ 0.98, MAD < 0.01, pHash ≤ 5 (pixel-level identical)
- Group B: SSIM < 0.95 OR MAD > 0.05 OR pHash > 10 (visible change)
- Group C: A-threshold met AND patch_id == 11 (link→span — smoking gun)

### Part E — CUA failure trace signature (DONE, local)

Script: `analysis/cua_failure_trace_validation.py`
Result: **42 / 54 CUA low-variant failures (77.8%) match link→span signature**
(≥ 8 clicks, ≥ 90% inert, ≥ 3 same-region loops, outcome=failure).
See `results/visual-equivalence/cua-failure-signature.md`.

## Pipeline fidelity — differences from the experimental runs

URL replay is **intentionally simpler** than production, but pipeline fidelity
is preserved on the two dimensions that matter for a visual-equivalence claim:

| Property | Production experiments | URL replay | Fidelity? |
|---|---|---|---|
| Viewport | BrowserGym chromium default 1280×720 | Playwright chromium 1280×720 (explicit) | ✅ |
| Variant JS | `apply-low.js` applied via Plan D deferred hook | Same file, applied via direct `page.evaluate()` after load | ✅ (same code, simpler driver) |
| Login cookies | env.reset + monkey-patched ui_login | Direct Playwright context cookie injection | ✅ (same cookies, different injection path) |
| Navigation | Agent-triggered goto/click/fill | Direct `page.goto(url)` | ⚠️ (but irrelevant to rendering) |
| Pages reached | Depends on agent success | ALL agent-visited URLs (union) | ✅ stronger |
| Plan D context.route | Persists patches across SPA navigations | Not needed — single navigation per URL | ✅ single-navigation trivially patched |

The **only difference** that could matter for SSIM is that v2 doesn't re-apply
patches via MutationObserver (production does). This is fine because:
1. MutationObserver re-applies only when Magento/KnockoutJS mutates the DOM
   AFTER patches — a framework-timing effect, not a visual effect
2. For the screenshot moment, both approaches converge to the same DOM state:
   `apply-low.js` has run once, settled, no mutations pending
3. We wait longer in v2 (explicit 1500ms settle + 800ms post-patch settle)
   than production's 500ms defer, giving MORE time for framework stability

## Success criteria

Same as v1 plan §3.5, with larger N:

1. ≥ 9 of 13 patches are **Group A** (visually identical)
2. Patch 11 is **Group C** (visually identical, functionally broken — smoking gun)
3. Group B patches (3, 9, possibly 6) are few and identified
4. **Aggregate base-vs-low SSIM ≥ 0.85** across ≥ 80% of agent-visited URLs
5. ≥ 60% of CUA low failures show the link→span signature (ALREADY 77.8%)

## Runtime estimate

- Part A (done): 2 minutes
- Part B (aggregate): 137 URLs × 2 variants × ~5s = ~25 min
- Part C (ablation): 4 URLs × 14 captures × ~5s = ~5 min
- Upload to S3: ~1 min
- Local analysis: < 1 min

**Total: ~30 minutes on EC2 for all screenshots.**

## Deliverables

1. `scripts/extract_agent_urls.py` — URL extraction ✅
2. `scripts/replay-url-screenshots.py` — Part B replay driver
3. `scripts/replay-url-patch-ablation.py` — Part C ablation driver
4. `src/variants/patches/inject/apply-low-individual.js` — single-patch selector ✅
5. `analysis/visual_equivalence_analysis.py` — SSIM/pHash/MAD + Group A/B/C ✅
6. `analysis/cua_failure_trace_validation.py` — Part E link→span signature ✅
7. `docs/analysis/visual-equivalence-validation.md` — paper-ready writeup

## Relationship to original bridge captureMode

The `browsergym_bridge.py captureMode` hook from commit f211198 still works and
remains available for anyone who wants the literal "first-observation state via
the production bridge" capture. URL replay gives **more** evidence than bridge
capture (137 pages vs 26 start pages). We keep both; URL replay is primary, bridge
capture is a cross-check if reviewers challenge "do your replay screenshots match
what BrowserGym would actually render?"
