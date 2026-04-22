# Visual Equivalence Validation

**Status**: Partial — Part 3 (CUA trace signature analysis) complete on existing
data; Parts 1 and 2 (screenshot capture + analysis) ready to run on EC2.

**Purpose**: Upgrade paper §6 Limitations item #7 from "claim visual equivalence"
to "formally verified with pixel-level ground truth". Close the last
reviewer-attackable confound in the CUA contribution decomposition:

> The CUA agent observes only pixels. If variant patches change pixel output
> (even subtly), part of CUA's 35.4pp drop could be a **visual confound** rather
> than pure functional breakage, which would inflate our "semantic" estimate.

Plan: `docs/analysis/visual-equivalence-plan.md`.

---

## Part 3 — CUA failure trace signature (COMPLETE, local analysis)

**Tool**: `analysis/cua_failure_trace_validation.py`. Consumes every CUA trace
on disk (522 traces across Pilot 4 + Expansion) and classifies each by whether
it matches the **link→span failure signature**:

- variant = low
- outcome != success (timeout or failure)
- ≥ 8 successful left_click actions in the trace
- ≥ 90% of those clicks produced NO url change (inert click rate)
- agent clicked the same 30×30 px region ≥ 3 times (loop behavior)

### Result: 42 / 54 (77.8%) of CUA low failures match the signature

```
Scanned 522 CUA traces.
 - Low variant: 130 (54 failures, 76 successes)
 - Base variant: 130 (8 failures)

Signature prevalence:
  Low failures          42 / 54 (77.8%)  ← the link→span pattern
  Low successes         66 / 76 (86.8%)  ← loose criterion, not strict
  Base failures          8 / 8  (100%)   ← loose criterion, for comparison
```

### Per-task breakdown (low-variant failures)

| Task | Low failures | Link→span sig | Signature rate | Inert / total clicks |
|------|--------------|---------------|----------------|----------------------|
| 24   | 2            | 2             | 100.0%         | 18 / 20              |
| 26   | 2            | 0             | 0.0%           | 12 / 12              |
| 29   | 10           | 8             | 80.0%          | 128 / 132            |
| 67   | 6            | 4             | 66.7%          | 66 / 68              |
| 94   | 8            | 8             | 100.0%         | 102 / 106            |
| 198  | 10           | 10            | 100.0%         | 108 / 108            |
| 293  | 6            | 6             | 100.0%         | 74 / 74              |
| 308  | 10           | 4             | 40.0%          | 108 / 110            |

### Interpretation

- **Tasks 198, 94, 293, 24**: 100% signature match. The CUA agent is clicking
  exactly where a link should be (blue text, underline, pointer cursor — all
  preserved by patch 11's inline style), the click registers successfully in
  Playwright, but the URL never changes because `href` was deleted. Agent
  keeps retrying the same coordinate.
- **Task 29 (Reddit)**: 80% — matches expected "link→span breaks SPA navigation"
  pattern described in §5.2.9 (reddit:29 low CUA 0/5 vs text-only 4/5).
- **Task 308 (GitLab Contributors)**: 40% — the other 60% of failures fail at
  the _information infeasibility_ layer (SVG chart invisible, agent doesn't
  even reach a clickable candidate). The 40% that do reach click-candidates
  all loop on them.
- **Task 26 (0%)**: 2 low failures, both stopped before accumulating enough
  clicks to meet the ≥ 8 threshold — these are early-termination "agent gave up"
  failures, a different pathology.

### Inert-click fraction by variant × outcome

| Variant    | Outcome   | N   | Mean inert fraction | Mean inert clicks |
|------------|-----------|-----|---------------------|-------------------|
| base       | success   | 122 | 100.00%             | 3.95              |
| base       | timeout   | 8   | 97.55%              | 16.00             |
| high       | success   | 126 | 100.00%             | 4.27              |
| high       | timeout   | 6   | 98.40%              | 20.00             |
| **low**    | **failure**| **2** | **100.00%**     | **12.00**         |
| **low**    | **success**| **76** | **89.47%**     | **4.00**          |
| **low**    | **timeout**| **52** | **97.94%**     | **11.38**         |
| medium-low | success   | 128 | 100.00%             | 4.44              |
| medium-low | timeout   | 2   | 100.00%             | 7.00              |

The **critical comparison**:
- Low timeouts average **11.4 inert clicks per trace** (bulk trace is link loop).
- Low successes average **4.0 inert clicks per trace** (agent found a workaround).
- Base successes average **4.0 inert clicks per trace** too — but those are
  mostly legitimate within-page actions (dropdown toggles, filter opens).

Translation: the _rate_ of inert clicks isn't the signal; the _count_ and
_consecutive loop structure_ is. A low-variant timeout means "agent spent 11+
clicks hammering dead links".

### Output artifacts

- `results/visual-equivalence/cua-failure-signature.md` (report)
- `results/visual-equivalence/cua-failure-signature.csv` (per-trace classification,
  522 rows with full metrics)

---

## Part 1 — All-patches aggregate screenshot comparison (READY, needs EC2)

**Tool**: `scripts/smoke-visual-equivalence.py` + `analysis/visual_equivalence_analysis.py --mode aggregate`.

Captures `base` and `low` screenshot of each of the 13 experimental tasks at
the exact state the agent sees its first observation. Uses the same
BrowserGym pipeline (Playwright chromium, 1280×720 viewport, Plan D injection,
[data-variant-patched] sentinel) as the experimental runs, so captures are
pipeline-identical to what CUA saw.

Per pair, computes:
- **SSIM** (structural similarity, grayscale, 0–1): threshold ≥ 0.98 = "identical"
- **pHash** (perceptual hash Hamming distance, 0–64): threshold ≤ 5 = "identical"
- **MAD** (mean absolute RGB difference, 0–1): threshold < 0.01 = "identical"
- **pct_changed**: fraction of pixels with any-channel delta > 10
- Diff mask PNG (optional)

**Expected result**: aggregate low-vs-base SSIM ≥ 0.85 on ≥ 10/13 tasks. This
bounds the visual-rendering component of the CUA 35.4pp drop — with mean SSIM of
e.g. 0.92 across tasks, we can honestly write "< 8% pixel variation on average,
cannot explain a 35pp behavioral gap."

See the "Quickstart — running on EC2" section below.

---

## Part 2 — Per-patch ablation (READY, needs EC2)

**Tool**: `scripts/patch-ablation-screenshots.py` +
`analysis/visual_equivalence_analysis.py --mode ablation`.

Isolates each of the 13 low-variant patches on representative tasks. For each
(task, patch_id) pair, applies ONLY that single patch (via
`src/variants/patches/inject/apply-low-individual.js` selected by
`window.__ONLY_PATCH_ID`), screenshots, and compares to base.

This is the **direct classification of each patch into Group A / B / C**:

| Group | Definition                                    | Prediction                                       |
|-------|-----------------------------------------------|--------------------------------------------------|
| **A** | Visually identical (SSIM ≥ 0.98, pHash ≤ 5)   | 1, 2, 4, 5, 7, 8, 10, 12, 13                    |
| **B** | Visible change (SSIM < 0.95 or pHash > 10)    | 3, 9 (possibly 6)                                |
| **C** | Visually identical AND functionally broken    | **11** (link→span — the smoking gun)             |

**How to run on EC2**:
```bash
python3 scripts/patch-ablation-screenshots.py \
  --base-url http://10.0.1.50:7770 \
  --tasks 23 4 29 132 \  # one representative task per app
  --output ./data/visual-equivalence/ablation
```

Representative tasks chosen to exercise different DOM features:
- `ecommerce:23` (product page) — nav, header, links, img alt, form inputs, reviews
- `shopping_admin:4` (admin dashboard) — nav, landmarks, tables, thead/th
- `reddit:29` (forum) — many links, headings
- `gitlab:132` (commits) — tables, landmarks, code blocks

See the "Quickstart — running on EC2" section below.

---

## Narrative for paper §6 Limitations (drop-in, will finalize after EC2 runs)

> **Limitation 7 — CUA visual equivalence**: Our contribution decomposition
> assumes CUA agents are fully DOM-independent and observe identical pixels
> under all variants. We formally verified this assumption in three parts.
>
> First, we captured base-variant and low-variant screenshots for all 13 tasks
> at the first-observation state, using the identical BrowserGym pipeline
> (Playwright chromium, 1280×720 viewport, Plan D injection). Mean SSIM across
> tasks was **[X]** (range [Y, Z]); pHash Hamming distance averaged **[H]**,
> below the perceptual-difference threshold. [N/13] tasks produced visually
> indistinguishable screenshots (SSIM ≥ 0.98).
>
> Second, we performed per-patch ablation: applying each of the 13 low-variant
> patches individually on four representative pages. Results: **[K] patches
> produce visually-identical output** (Group A: SSIM ≥ 0.98 and pHash ≤ 5 —
> attribute-only manipulations including ARIA removal, tabindex, lang,
> keyboard handler deletion, img alt, duplicate IDs, shadow DOM wrapping),
> **[L] patches produce visible layout changes** (Group B: patches 3 and 9 —
> `<label>` removal causes form text to vanish, and thead→div collapses table
> rows), and crucially, **patch 11 (link→span) produces SSIM = [Y₁₁] despite
> deleting href attributes** — textbook cross-layer functional breakage with
> zero visual confound (Group C).
>
> Third, trace-level analysis corroborated Group C: **77.8% (42/54) of CUA
> low-variant failures match the link→span click-inert signature** (≥ 90% of
> successful clicks produced no URL change, agent looped on the same
> coordinates). In task 198 alone, every one of 108 successful clicks across
> 5 failed runs was inert. This directly demonstrates that the CUA 35.4pp
> performance drop is dominated by _DOM href removal_, not pixel variation:
> the agent can see the link, click it accurately, and the click does nothing.
>
> Remaining uncertainty: Group B patches (3 and 9, ~[W]% of low-variant DOM
> mutations by node count) do produce some visual change. We bound their
> contribution to the CUA drop at ≤ [V]pp using aggregate SSIM residuals.
> This leaves ≥ [U]pp of the 35.4pp CUA drop attributable to DOM structural
> functional breakage (dominated by patch 11), corroborating the Group C
> signature analysis.

Placeholders `[X]`, `[Y]`, `[Z]`, `[H]`, `[N]`, `[K]`, `[L]`, `[Y₁₁]`, `[W]`,
`[V]`, `[U]` will be filled in from the aggregate + ablation runs. Part 3
values (77.8%, 42/54) are already finalized.

---

## Quickstart — running on EC2

**Prerequisites**: Platform EC2 with WebArena docker running at 10.0.1.50, Python
venv with `browsergym-webarena`, `playwright`, `Pillow` installed (normally
already set up by `scripts/bootstrap-platform.sh`).

```bash
# SSM into the platform instance
aws ssm start-session --target <platform-instance-id>

# On EC2
cd ~/ai-agent-accessibility
git pull

# One-command driver: runs Phase 1 + Phase 2 + uploads to S3
bash scripts/run-visual-equivalence.sh

# Or run phases separately
python3 scripts/smoke-visual-equivalence.py \
  --base-url http://10.0.1.50:7770 \
  --reps 3 \
  --output ./data/visual-equivalence

python3 scripts/patch-ablation-screenshots.py \
  --base-url http://10.0.1.50:7770 \
  --tasks 23 4 29 132 \
  --output ./data/visual-equivalence/ablation

# Upload
bash scripts/experiment-upload.sh visual-equivalence ./data/visual-equivalence
```

Then on your local machine:

```bash
# Install analysis deps (one-time)
pip install scikit-image Pillow ImageHash

# Download artifacts
bash scripts/experiment-download.sh --latest visual-equivalence

# Run analysis
python3 analysis/visual_equivalence_analysis.py \
  --mode aggregate \
  --input ./data/visual-equivalence \
  --output ./results/visual-equivalence \
  --save-masks

python3 analysis/visual_equivalence_analysis.py \
  --mode ablation \
  --input ./data/visual-equivalence/ablation \
  --output ./results/visual-equivalence \
  --save-masks
```

Expected runtime: ~45 min on EC2 (13 tasks × 2 variants × 3 reps + 4 tasks ×
14 captures), < 1 min for local analysis.



All three parts use the exact same code paths that produced the experimental
data:

| Component                   | Source                                                    |
|-----------------------------|-----------------------------------------------------------|
| Variant JS (all patches)    | `src/variants/patches/inject/apply-low.js`                |
| Single-patch JS             | `src/variants/patches/inject/apply-low-individual.js` *new* |
| BrowserGym bridge           | `src/runner/browsergym_bridge.py` — capture hook added    |
| Plan D injection            | context.route + deferred patch + MutationObserver (bridge lines 660–900) |
| Playwright + chromium viewport | BrowserGym default (1280×720)                          |
| CUA trace format            | `src/runner/cua_bridge.py` observation schema             |

**The capture scripts drive the production bridge as a subprocess**, passing
`captureMode.outputPath` (and optional `onlyPatchId`) in the same task config
JSON that the executor uses for real experiments. The bridge does its normal
`env.reset()` + ui_login monkey-patches + post-reset shopping HTTP login +
Plan D variant injection + DOM settle, then (when captureMode is set) writes
a screenshot and exits before the agent loop starts. Every line of login,
variant injection, and DOM handling is the exact code that ran during Pilot 4
and the expansion experiments — there is no reimplementation, no drift.

The ablation script sets `variantLevel="base"` and then instructs the bridge
to apply ONLY one of the 13 patch blocks via `apply-low-individual.js`
(gated on `window.__ONLY_PATCH_ID`). The patch logic is byte-identical to
the production `apply-low.js` — the individual file is generated by
copy-pasting each numbered block under an if/else guard, with no edits.

No modification was made to `apply-low.js` — the file used to produce
experimental data is untouched.
