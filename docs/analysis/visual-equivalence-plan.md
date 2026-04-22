# Visual Equivalence Validation — Experiment Plan

**Date**: 2026-04-22
**Goal**: Upgrade §6 Limitations #7 from "claim visual equivalence" to "formally verified with pixel-level ground truth." Close the last reviewer-attackable hole in the CUA contribution decomposition.

---

## 1. Research question

§5.3 claims a causal decomposition: text-only 55.4pp drop − CUA 35.4pp drop = 20.0pp attributable to the semantic pathway (a11y tree), leaving ~35.4pp attributable to cross-layer functional breakage (href removal). This argument rests on the assumption that CUA is **fully DOM-independent** — it sees only raw pixels. If variant patches change pixel output (even subtly), then part of CUA's 35.4pp drop could be a **visual confound** rather than pure functional breakage, which would inflate our "semantic" estimate.

§6 Limitations currently hedges:

> "our contribution decomposition assumes CUA agents are fully DOM-independent... minor visual rendering differences across variants (e.g., subtle layout shifts from element substitution) may introduce a small confound. We mitigate this concern by noting that all variant patches are CSS-preserving DOM substitutions designed to maintain visual equivalence... but pixel-perfect rendering identity across variants is not formally guaranteed."

The phrase "not formally guaranteed" is the reviewer attack surface. This experiment formally verifies it.

## 2. Hypothesis (three-group prediction)

Each of the 13 low-variant patches falls into one of three visual-impact groups:

| Group | Prediction | Patches | Mechanism |
|-------|-----------|---------|-----------|
| **A** Visually identical (SSIM ≥ 0.98) | pixel-level match, no layout shift | 1 (nav→div), 2 (aria-* delete), 4 (keyboard handlers), 5 (shadow DOM wrap), 7 (img alt), 8 (tabindex), 10 (html lang), 12 (duplicate IDs), 13 (onfocus blur) | attribute-only or invisible wrapping |
| **B** Visible change (SSIM < 0.95) | text disappears or table reflows | 3 (label.remove), 9 (thead→div) | element removal or flow-model change |
| **C** Visually identical but functionally broken (SSIM ≥ 0.98, click inert) | blue/underline/cursor preserved via inline style, `href` deleted | 11 (link→span) | DOM substitution with CSS preservation |
| ? Ambiguous | font size preserved by inline style, but heading margins may shift | 6 (h1→div) | needs empirical test |

**Group C is the paper's hard evidence**: if patch 11 alone produces SSIM ≥ 0.98 but CUA's click at the preserved coordinate produces no navigation, that is textbook cross-layer functional breakage with zero visual confound — exactly the "Same Barrier" claim operationalized at the pixel level.

## 3. Design

### 3.1 Part 1 — All-patches comparison (13 tasks × 2 variants)

For each of the 13 tasks: capture `base` and `low` screenshot at the agent's first-observation state. This measures the aggregate visual difference the CUA agent actually sees in the experiment.

- 13 tasks × {base, low} = **26 screenshots**
- Same pipeline: BrowserGym `gym.make("browsergym/webarena.<id>")` → `env.reset()` → login flow → Plan D injection → 500ms settle → `page.screenshot()`
- Same viewport: Playwright chromium default 1280×720 (matches experiment)
- Per-pair metrics: SSIM, pHash hamming distance, per-pixel mean absolute difference (MAD), diff mask image

### 3.2 Part 2 — Per-patch ablation (isolates Group A/B/C)

For each of the 13 individual patches: apply only that patch (not all 13), screenshot, compare to base.

- 1 representative task (e.g. `ecommerce:23` — product page with nav/header/links/form/table) × 13 patches × 1 rep = **13 screenshots + 1 base**
- Uses a patch selector parameter in `apply-low.js` — refactor to expose individual patch functions. Or: build 13 ad-hoc single-patch scripts. (Simpler: fork `apply-low.js` with an `only` parameter.)
- Per-patch metrics: SSIM, MAD, diff mask, bounding box of visual changes

### 3.3 Part 3 — CUA failure trace cross-validation

From CUA low-variant failures (27 cases total, of which ~17 are reportedly cross-layer functional breakage per §5.2.9), quantify how many show the **link→span signature**:
- Agent clicked a coordinate that is visually a link (blue underlined text)
- Click succeeded (no Playwright error, mouse registered)
- Page did not navigate (URL unchanged, no new DOM load)

This is the agent-side corroboration of Part 2. Together they say: "patches visually identical (Part 2) + agent clicked the pixel anyway (Part 3) → only DOM deletion of `href` could explain the failure."

### 3.4 Metrics

- **SSIM** (scikit-image `structural_similarity`, grayscale, data_range=255): 0–1, higher is more similar. Threshold: ≥ 0.98 = "identical for humans".
- **pHash** (perception hashing via `imagehash.phash`, 8-bit): Hamming distance ≤ 5 = "perceptually identical". Robust to anti-aliasing noise.
- **MAD** (mean absolute pixel difference on RGB, normalized to 0–1): < 0.01 = "effectively identical", > 0.05 = "clearly different".
- **Diff mask**: per-pixel threshold on abs difference, saved as PNG for qualitative review.

### 3.5 Success criteria

The experiment "works" — i.e., the paper claim is supported — if:
1. **≥ 9/13 patches are Group A** (SSIM ≥ 0.98, pHash ≤ 5): we can honestly claim "most patches are visually identical".
2. **Patch 11 is Group C** (SSIM ≥ 0.98 AND known-broken functionality): smoking gun available.
3. **Group B is small and identifiable** (patches 3, 9, possibly 6): we disclose them as a caveat, not hide them.
4. **Aggregate low-vs-base SSIM per task ≥ 0.85** on ≥ 10/13 tasks: the full variant (all 13 patches combined) still produces mostly-similar screenshots, bounding the size of the visual confound.
5. **≥ 60% of CUA low-variant failures show link→span signature**: corroborates Group C functional-only failure mode.

## 4. Deliverables

1. **`scripts/smoke-visual-equivalence.py`** — captures base+low screenshots for all 13 tasks on EC2. Runs inside the existing bridge infrastructure so pipeline is identical. Saves to `./data/visual-equivalence/<task>/{base,low}.png`.
2. **`scripts/patch-ablation-screenshots.py`** — applies each of 13 patches individually on ecommerce:23, saves `./data/visual-equivalence/ablation/patch_<N>.png` + `base.png`.
3. **`analysis/visual_equivalence_analysis.py`** — reads screenshots, computes SSIM/pHash/MAD, produces `results/visual-equivalence-report.md` with per-patch classification and per-task aggregate table.
4. **`analysis/cua_failure_trace_validation.py`** — scans CUA low-variant failure traces, classifies each by link→span signature (click coord → URL unchanged → screenshot diff minimal).
5. **`docs/analysis/visual-equivalence-validation.md`** — final writeup, drop-in for paper §6.

## 5. Pipeline fidelity requirements

Per `project-context.md` "Consistency requirements" — any mid-experiment change to bridge code, variant scripts, or browsergym version invalidates comparability. For this validation we:

- **Use the unmodified current `browsergym_bridge.py`** to drive env.reset + login + Plan D. The capture script hooks in AFTER initial observation is sent but BEFORE the agent loop starts.
- **Use the same `apply-low.js` that produced the experimental data** (git hash at time of pilot4 + expansion). Do not touch the file.
- **Capture at the same instant the bridge emits the first observation** — Plan D deferred patch has already fired (window.load + 500ms + MutationObserver settling), so the screenshot matches what the CUA agent sees in step 0.
- **For patch ablation**, refactor `apply-low.js` into a version that accepts an `ONLY_PATCH_ID` env var and runs only one of the 13 patch blocks. Do not modify the production `apply-low.js`; build a separate `apply-low-individual.js`.

## 6. Risk / mitigation

| Risk | Mitigation |
|------|-----------|
| Screenshot state varies due to lazy-loaded content (reddit post list randomizes, magento has rotating banners) | Capture 3 replicates per (task, variant), use the pair with minimum within-variant variance |
| Plan D injection has 500ms + MutationObserver; screenshot may capture mid-flight | Wait for `[data-variant-patched="true"]` sentinel on `<html>` before screenshotting (same as observation extraction wait) |
| ecom:23 may not exercise all 13 patches (e.g., no table → patch 9 invisible there) | Use 2 representative tasks for ablation: ecom:23 (product page — exercises links, form labels, img alts, nav, headings) + admin:4 (admin page — exercises tables, admin navigation) |
| Current EC2 may not be available | Build for portable execution — scripts accept `--webarena-url` arg; plan doc references S3 upload/download workflow |
| CUA failure trace classification requires per-step click coords + URL before/after | Traces already record these (we have 260 CUA traces on disk at `data/expansion-cua/` + `data/pilot4-cua/`). Use existing JSON format. |

## 7. Execution checklist

- [ ] Phase 0: Build ablation script (`apply-low-individual.js` + `patch-ablation-screenshots.py`) — local dev, test on WebArena if available
- [ ] Phase 1: Capture script (`smoke-visual-equivalence.py`) — local dev, run on EC2
- [ ] Phase 2: Analysis (`visual_equivalence_analysis.py`) — local dev, run on local artifacts
- [ ] Phase 3: CUA trace validator — local only, reads existing CUA traces
- [ ] Phase 4: Write `visual-equivalence-validation.md` — drops into paper §6

## 8. Expected outcome for the paper

Replaces §6 Limitations #7 with a short validation subsection:

> We formally validated visual equivalence by capturing screenshots at the first-observation state for all 13 tasks under both `base` and `low` variants, using the identical BrowserGym pipeline (Playwright chromium, 1280×720 viewport, Plan D injection). Per-patch ablation isolated each of the 13 low-variant manipulations on a representative page. Of the 13 patches, **X produce visually-identical output (SSIM ≥ 0.98), Y produce visible layout changes (SSIM < 0.95), and patch 11 (link→span) produces SSIM ≥ 0.98 despite deleting functional href attributes** — textbook cross-layer functional breakage with zero visual confound. Aggregate low-vs-base SSIM across all 13 tasks averages Z (min, max), bounding the visual-rendering component of the CUA 35.4pp drop at below W pp. The remaining ≥ V pp is attributable to DOM structural functional breakage, corroborated by trace analysis showing U% of CUA low-variant failures match the link→span click-inert signature.

The "not formally guaranteed" clause becomes "formally verified via pixel-level ground truth."
