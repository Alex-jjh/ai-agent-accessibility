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


---

## v2.1 — Reviewer-grade hardening (2026-04-22)

Three P0 fixes and three P1 fixes applied after a simulated CHI reviewer
reread of the v2 plan. The changes are all in-code + documented here so the
plan is pre-registered before Phase B/C runs.

### P0-1: Phase C URL coverage 4 → 15

Rationale: per-patch SSIM attribution on only 4 URLs cannot claim to
generalize. We now test each patch on 15 URLs spanning all 4 WebArena apps:

- shopping × 4 (home, product, category, account dashboard)
- shopping_admin × 3 (orders grid, dashboard, products grid)
- reddit × 3 (home, forum listing, submission detail)
- gitlab × 4 (project, commits, graphs, issues)
- controls × 1 (kiwix)

This gives per-patch mean±σ, which we report in the §6 table and in the
paper's supplementary. `REPRESENTATIVE_URLS` in
`scripts/replay-url-patch-ablation.py` is the authoritative list.

### P0-2: Baseline-noise floor via `base` vs `base2`

Rationale: Playwright two-shot captures of the SAME URL under the SAME
variant are not pixel-identical (dynamic content: banner rotation, timestamps,
CSRF tokens, animation tails). Without knowing this intrinsic noise, a
base-vs-low SSIM of 0.97 is ambiguous.

Implementation:
- `replay-url-screenshots.py --variants base base2 low` (default) captures
  the same URL under base twice (independent contexts) plus once under low.
- `visual_equivalence_analysis.py` runs a Mann-Whitney U test comparing the
  base-vs-low SSIM distribution to the base-vs-base2 baseline distribution.
- The paper reports both: the mean SSIM AND its statistical distance from
  intrinsic rendering noise. "base-vs-low SSIM is within baseline noise
  (U=…, p=…)" is the defensible claim.

### P0-3: Session-lost detection + periodic re-login

Rationale: over 274 sequential captures a login cookie can silently expire,
producing a mid-run mix of "authenticated pages" and "redirect-to-login pages".

Implementation:
- `capture_one()` sets `session_lost=True` if `final_url` contains
  `/login`, `/sign_in`, `/customer/account/login`, or `/admin/auth/login`
  AND the original URL didn't. Such captures are excluded from analysis.
- Main loop re-logins every 50 URLs (`--relogin-every`) as a refresh.
- On a single session-lost hit, the app is re-logged-in and the capture
  retried once with `after_relogin=True` recorded in the manifest.

Captures that failed after retry are reported in the §6 drop-in as
"excluded from analysis: session_lost=N / total".

### Pre-registered thresholds (P1-2)

Before data collection, we fix the Group A/B/C boundaries. These are
documented here and hard-coded in
`analysis/visual_equivalence_analysis.py::PREREGISTERED_THRESHOLDS`.

**Default thresholds** (used if baseline data absent):

| Bound                 | SSIM     | MAD     | pHash  | LPIPS   |
|-----------------------|----------|---------|--------|---------|
| Group A (identical)   | ≥ 0.98   | < 0.01  | ≤ 5    | ≤ 0.05  |
| Group B (visible Δ)   | < 0.95   | > 0.05  | > 10   | > 0.15  |

**Data-driven thresholds** (preferred, derived from base-vs-base2 baseline):

- Group A floor = μ(baseline) − 2σ for each metric (≈98% of intrinsic noise
  classifies as A)
- Group B cutoff = μ(baseline) − 4σ (clearly beyond noise)

The analysis script writes `thresholds.json` during the aggregate step and
the ablation step reuses it via `--thresholds-json`. This guarantees both
phases use identical, baseline-derived cutoffs.

**Group C** is a conjunction: Group A metrics + patch_id = 11 (link→span).
It is not a threshold; it's a definition that identifies visually-identical
changes that destroy navigation.

### P1-1: LPIPS as second perceptual metric

Rationale: SSIM is structure-sensitive and can false-positive on minor
translation (element shifted 2 px). LPIPS is learned-perceptual and
correlates with human judgment more directly.

Implementation: lazy-loaded via `analysis.visual_equivalence_analysis.compute_lpips`
on first call. Added as an optional column; if `lpips` package is not
installed, the metric is simply omitted. Classifier uses LPIPS as an extra
gate in the Group A AND-chain when present.

### P1-3: Direct click-probe for Group C

Rationale: Group C currently joins two independent signals
(SSIM ≈ 1.0 + CUA 77.8% trace signature). A third, direct signal is cheap:
actually click on the same (x, y) coordinates under base and under patch-11
only, record whether the page navigated away.

Implementation: `scripts/replay-url-click-probe.py`
- For each of the 15 URLs: find first visible `<a href>` in the viewport,
  capture bbox center coords
- Click at those coords under base → assert page navigated
- Navigate to same URL, apply ONLY patch 11, click at same coords →
  assert page DID NOT navigate
- Success criterion: ≥ 80% of URLs show "base navigated + patch 11 inert"

The paper can then state: "On N/15 URLs, identical-SSIM patch 11 produces
pixel-identical rendering yet destroys click-induced navigation
(final_url unchanged after 3s wait)."

## Execution checklist (updated)

1. [x] Scripts updated with P0/P1 fixes
2. [x] Push to origin/master
3. [ ] Install lpips + torch on Platform EC2 (bootstrap follow-up)
4. [ ] Phase B: `replay-url-screenshots.py --variants base base2 low`
       (137 URLs × 3 variants ≈ 35 min)
5. [ ] Phase C: `replay-url-patch-ablation.py` (15 URLs × 14 captures ≈ 12 min)
6. [ ] Phase D: `replay-url-click-probe.py` (15 URLs × 2 clicks ≈ 6 min)
7. [ ] Upload to S3 + download locally
8. [ ] Run `visual_equivalence_analysis.py --mode aggregate` → derives thresholds
9. [ ] Run `visual_equivalence_analysis.py --mode ablation --thresholds-json …`
10. [ ] Open gallery.html + flag edge cases
11. [ ] Write §6 drop-in with SSIM numbers, Mann-Whitney result, Group breakdown
