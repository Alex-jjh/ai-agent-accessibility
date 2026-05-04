# Screenshot Audit Guide — For Human Reviewer

> **Purpose**: Visually verify that AMT operators produce the expected DOM
> changes while preserving (or intentionally altering) visual appearance.
> This audit supports the paper's claims about SSIM scores and the
> "Landmark Paradox" (L1 changes semantics but not visuals).
>
> **Time estimate**: 2–3 hours for full audit; 30 minutes for priority-only.
>
> **You do NOT need to run any code.** All screenshots are pre-captured PNG files.

---

## Available Screenshot Datasets

### Dataset 1: AMT Operator Audit (PRIORITY — use this)

**Location**: `data/archive/amt-audit-batch/`

**Structure**: 39 directories (13 tasks × 3 reps), each containing
before/after screenshots for all 26 operators.

```
data/archive/amt-audit-batch/
  batch-t4-r1/screenshots/
    L1_before.png    L1_after.png
    L2_before.png    L2_after.png
    ...
    ML1_before.png   ML1_after.png
    ...
    H1_before.png    H1_after.png
    ...
  batch-t4-r2/screenshots/
    (same structure)
  batch-t23-r1/screenshots/
    (same structure)
  ...
```

**What each file shows**:
- `{OP}_before.png` — the page BEFORE the operator is applied (base state)
- `{OP}_after.png` — the page AFTER the operator is applied

**Total**: 39 dirs × 26 operators × 2 (before/after) = **2,028 screenshots**

### Dataset 2: Visual Equivalence Replay (SECONDARY)

**Location**: `data/visual-equivalence/replay/`

**Structure**: 61 URL directories, each containing base.png, base2.png
(duplicate baseline for noise measurement), and low.png (all 13 L-operators
applied simultaneously).

```
data/visual-equivalence/replay/
  reddit__f-DIY__22cb7fbf/
    base.png     — page with no patches
    base2.png    — same page, second capture (noise baseline)
    low.png      — page with ALL Low operators applied
  gitlab__primer-design__793b74e0/
    base.png
    base2.png
    low.png
  ...
```

**Total**: 61 URLs × 3 screenshots = **183 screenshots**

### Dataset 3: Per-Patch Ablation (SECONDARY)

**Location**: `data/visual-equivalence/ablation-replay/`

**Structure**: 14 URL directories, each containing base.png + 13 individual
patch screenshots (patch_01 through patch_13, corresponding to L1–L13).

```
data/visual-equivalence/ablation-replay/
  reddit__f-books__54c48968/
    base.png       — no patches
    patch_01.png   — only L1 (landmark→div) applied
    patch_02.png   — only L2 (strip ARIA) applied
    ...
    patch_13.png   — only L13 (focus blur) applied
```

**Total**: 14 URLs × 14 screenshots = **196 screenshots**

### Dataset 4: CUA Agent Screenshots (LOW PRIORITY — known bug)

**Location**: `data/mode-a-shard-{a,b}-screenshots/cua-screenshots/`

**Note from Alex**: These only capture the LAST step of each CUA run, not
the initial page state. The before/after comparison is not valid for visual
equivalence purposes. **Skip this dataset.**

---

## Priority Audit Tasks

### Task 1: Verify "Landmark Paradox" (L1 SSIM=1.000)

**Claim**: L1 (landmark→div) produces SSIM=1.000 — the page looks
visually identical before and after landmark removal.

**What to check**:
1. Open `batch-t4-r1/screenshots/L1_before.png` and `L1_after.png`
2. Compare side by side. They should look **identical** to the human eye.
3. Repeat for 2–3 other tasks: `batch-t23-r1`, `batch-t132-r1`
4. **Expected**: No visible difference. Landmarks (`<nav>`, `<main>`,
   `<header>`, `<footer>`) are structural wrappers with no visual rendering.

**If you see a difference**: Note which task, which visual element changed,
and whether it's a layout shift or a content change. This would contradict
the SSIM=1.000 claim.

### Task 2: Verify L5 Visual Change (SSIM=0.803)

**Claim**: L5 (Shadow DOM wrap) produces SSIM=0.803 — significant visual
change because CSS cascade resets at the shadow boundary.

**What to check**:
1. Open `batch-t4-r1/screenshots/L5_before.png` and `L5_after.png`
2. You should see **visible differences**: buttons may lose styling,
   interactive elements may appear as unstyled text.
3. Repeat for `batch-t23-r1`, `batch-t94-r1`
4. **Expected**: Buttons, links, and form controls lose their styled
   appearance. The page looks "broken" but content text is still readable.

### Task 3: Verify L6 Visual Change (SSIM=0.908)

**Claim**: L6 (heading→div) produces SSIM=0.908 — moderate visual change
because headings lose their font-size styling.

**What to check**:
1. Open `batch-t4-r1/screenshots/L6_before.png` and `L6_after.png`
2. Headings (large bold text) should become normal-sized text.
3. **Expected**: Page structure is preserved but heading text shrinks to
   body text size. The page looks "flatter" but is still navigable.

### Task 4: Verify L11 Visual Preservation (SSIM=0.976)

**Claim**: L11 (link→span) produces SSIM=0.976 — links are replaced with
spans but blue underline styling is preserved via CSS.

**What to check**:
1. Open `batch-t23-r1/screenshots/L11_before.png` and `L11_after.png`
2. Links should still appear blue and underlined.
3. **Expected**: Visually near-identical. The only difference might be
   subtle cursor changes (pointer → default) that screenshots don't capture.

### Task 5: Verify H-operators are visually invisible (SSIM=1.000)

**Claim**: All High operators (H1–H8) produce SSIM=1.000 — enhancements
are purely semantic (ARIA attributes, skip-nav links) with no visual change.

**What to check**:
1. Open `batch-t4-r1/screenshots/H1_before.png` and `H1_after.png`
2. They should look **identical**.
3. Spot-check H2 (skip-nav), H4 (landmark roles), H8 (table scope).
4. **Exception**: H2 (skip-nav) injects a visually-hidden link at the
   bottom of the page. It should NOT be visible in the screenshot. If you
   see a "Skip to main content" link appearing, note it.

### Task 6: Per-Patch Ablation Spot Check

**What to check**:
1. Open `ablation-replay/reddit__f-books__54c48968/base.png`
2. Compare with `patch_01.png` (L1 only) — should look identical
3. Compare with `patch_05.png` (L5 only) — should show visual degradation
4. Compare with `patch_06.png` (L6 only) — headings should shrink
5. Compare with `patch_11.png` (L11 only) — links should still be blue

---

## Recording Your Findings

For each task above, record:

| Task | Operator | Task ID | Visual Match? | Notes |
|------|----------|---------|---------------|-------|
| 1 | L1 | t4-r1 | Yes/No | (describe any difference) |
| 1 | L1 | t23-r1 | Yes/No | |
| 2 | L5 | t4-r1 | Expected change? | (describe what changed) |
| ... | | | | |

**Key questions to answer**:
1. Does L1 really look identical before/after? (supports SSIM=1.000)
2. Does L5 show obvious visual breakage? (supports SSIM=0.803)
3. Does L11 preserve blue underline on links? (supports SSIM=0.976)
4. Are H-operators truly invisible? (supports SSIM=1.000)

---

## What This Audit Does NOT Cover

- **Agent behavior**: This audit only checks visual appearance, not whether
  agents succeed or fail. Agent behavior is covered by trace analysis.
- **A11y tree changes**: The DOM signature audit (12-dim vector) covers
  semantic changes. This audit covers only the visual layer.
- **CUA screenshots**: The CUA screenshots in `mode-a-shard-{a,b}-screenshots`
  have a known bug (only last step captured). Skip them.
