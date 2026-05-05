---
inclusion: auto
---

# CHI 2027 Submission Roadmap — Text-Only Expansion

> **Updated**: 2026-05-04 (evening session)
> **Deadline**: 2026-09-11 (CHI 2027 submission)
> **Days remaining**: ~130
> **Strategy**: Text-only primary, SSIM visual control, CUA composite-only

---

## Strategic Decision (2026-05-04)

### What changed
After 5 rounds of AI reviewer simulation, the core weakness is **13 tasks**.
Decision: expand to **50-100 tasks** via a Smoker → Filter → Manipulate pipeline.

### What we're NOT doing
- ❌ No new CUA runs (baseline 48.2% in Mode A = too noisy)
- ❌ No new SoM runs (baseline 27.7% = near random)
- ❌ No new models (budget constraint + diminishing returns)

### What we ARE doing
- ✅ Smoker: 684 tasks × base × text-only × 5 reps (identify solvable tasks)
- ✅ Filter: keep tasks with ≥3/5 base success (majority vote gate)
- ✅ Manipulate: filtered tasks × 26 operators × text-only × 3 reps (Claude + Llama 4)
- ✅ DOM audit: filtered tasks × 26 operators × before/after screenshots (SSIM)
- ✅ Visual equivalence: SSIM replaces CUA as "visual control" evidence

### Paper narrative adjustment
- **Primary evidence**: text-only (Claude + Llama 4) on 50-100 tasks
- **Visual control**: SSIM from DOM audit screenshots (mathematical proof of visual equivalence)
- **Composite CUA**: retained for pathway decomposition (baseline 93.8%, clean)
- **Mode A CUA/SoM**: supplementary/appendix only

---

## Execution Pipeline

### Stage 1: Smoker (Base Solvability Gate)

**Config**: `config-smoker-base-solvability.yaml`
**Cases**: ~684 tasks × 5 reps = 3,420 (only string_match eval tasks)
**Cost**: ~$300-400
**Time**: 1-2 days wall
**Output**: `data/smoker-base-solvability/`

**Solvability criteria**:
- ≥3/5 reps succeed (majority vote)
- Answer is consistent across reps (no GT drift)
- No state mutation required (info retrieval only)

**Expected yield**: ~150-250 tasks pass (based on WebArena literature: ~30-40% base solvability for Claude Sonnet on string_match tasks)

### Stage 2: Filter

**Script**: `scripts/analyze-smoker.py` (to be written)
**Input**: smoker results
**Output**: filtered task list + `config-manipulation-filtered.yaml`

**Additional filters** (applied after majority-vote gate):
- Exclude tasks where answer varies between reps (GT instability)
- Exclude tasks requiring >25 steps at base (too complex, timeout risk)
- Stratify by app (ensure ≥10 tasks per app)
- Target: 50-100 tasks

### Stage 3: Manipulate (Full AMT Experiment)

**Config**: `config-manipulation-filtered.yaml` (auto-generated from Stage 2)
**Cases**: ~80 tasks × 26 ops × 3 reps × 2 models = ~12,480
**Cost**: ~$800-1,200
**Time**: 3-5 days wall (parallel shards)
**Output**: `data/manipulation-v2/`

**Docker state management**:
- Configure `WA_FULL_RESET=1` if available
- Or: restart Docker containers every 500 cases
- Verify GT on first rep of each new task before continuing

### Stage 4: DOM Audit (Visual Equivalence)

**Script**: `scripts/audit-operator.ts` (existing)
**Cases**: ~80 tasks × 26 ops × 3 reps = 6,240 screenshots
**Cost**: $0 (Playwright only, no LLM)
**Time**: ~4-6 hours
**Output**: `data/dom-audit-v2/` with before/after PNGs + SSIM values

**This replaces CUA as visual control**:
- Per-operator SSIM proves visual equivalence mathematically
- Human reviewer spot-checks screenshots (see `docs/screenshot-audit-guide.md`)
- No need for CUA agent to "indirectly prove" visual invariance

### Stage 5: Analysis + Paper Update

**Scripts**: existing `amt_statistics.py` + `audit-paper-numbers.py` (extended)
**Tasks**:
1. Compute per-operator significance on expanded task set
2. Recompute signature alignment with more data points
3. Verify compositional results still hold (or re-run C.2 on expanded tasks)
4. Update all paper numbers
5. Regenerate figures F4-F9

---

## Paper Writing Tasks (parallel with experiments)

### Immediate (this week)

| Task | Owner | Status |
|------|-------|--------|
| Screenshot audit (existing data, L1/L5/L6/L11) | Alex | ⬜ |
| Send PDF + change summary to Brennan | Alex | ⬜ |
| Adjust paper narrative: CUA → supplementary, SSIM → primary visual control | Kiro | ⬜ |

### After Smoker completes

| Task | Owner | Status |
|------|-------|--------|
| Write `scripts/analyze-smoker.py` (filter script) | Kiro | ⬜ |
| Review smoker results, decide final task count | Alex | ⬜ |
| Generate manipulation config | Kiro | ⬜ |

### After Manipulation completes

| Task | Owner | Status |
|------|-------|--------|
| Run analysis pipeline on new data | Kiro | ⬜ |
| Update paper numbers (§4, §5) | Kiro | ⬜ |
| Regenerate figures F4-F9 | Kiro | ⬜ |
| Update abstract + conclusion | Kiro | ⬜ |
| Page compression (target: 12 pages body) | Kiro | ⬜ |

### Pre-submission (August)

| Task | Owner | Status |
|------|-------|--------|
| Brennan review + feedback incorporation | Alex + Brennan | ⬜ |
| Figure readability check (print PDF) | Alex | ⬜ |
| Supplementary materials package | Kiro | ⬜ |
| Final number audit | Kiro | ⬜ |
| LaTeX format (submission template) | Kiro | ⬜ |
| CHI 2027 submission | Alex | ⬜ Deadline: 09-11 |

---

## Budget Tracker

| Item | Spent | Remaining |
|------|-------|-----------|
| Pilot 1-4 + expansion (historical) | ~$2,000 | — |
| Mode A + C.2 (current data) | ~$3,000-4,000 | — |
| Smoker (Stage 1) | — | ~$300-400 |
| Manipulation (Stage 3) | — | ~$800-1,200 |
| **Total** | ~$5,000-6,000 | ~$1,100-1,600 |

---

## Key Files

| File | Purpose |
|------|---------|
| `config-smoker-base-solvability.yaml` | Smoker config (684 tasks × base × 5 reps) |
| `config-manipulation-filtered.yaml` | To be generated after smoker |
| `scripts/analyze-smoker.py` | To be written: filter base-solvable tasks |
| `docs/screenshot-audit-guide.md` | Human reviewer guide for visual audit |
| `docs/statistical-methods-inventory.md` | 25 statistical procedures |
| `scripts/amt/audit-paper-numbers.py` | Reproducibility audit |
| `analysis/amt_statistics.py` | All inferential statistics |
| `task-site-mapping.json` | Task ID → site mapping (684 tasks) |

---

## Reviewer Concern Resolution (updated)

| Concern | Old resolution | New resolution |
|---------|---------------|----------------|
| 13 tasks too few | Power analysis + operator-centric argument | **50-100 tasks via smoker pipeline** |
| CUA baseline 48.2% | Explained in limitations | **CUA removed from Mode A primary; SSIM replaces as visual control** |
| SoM baseline 27.7% | Supplementary only | **Unchanged — supplementary only** |
| Ecological audit thin (34 sites) | Renamed "probe" | Optional: expand to 100+ sites if time permits |
| All other concerns | Already addressed in paper | Unchanged |

---

## Timeline

| Period | Activity |
|--------|----------|
| **05-04 → 05-10** | Deploy new burner account, run smoker |
| **05-10 → 05-14** | Analyze smoker, filter tasks, prepare manipulation config |
| **05-14 → 05-20** | Run manipulation experiment (Claude + Llama 4) |
| **05-20 → 05-24** | Run DOM audit (screenshots), analyze results |
| **05-24 → 06-07** | Update paper with new data, compress pages |
| **06-07 → 07-14** | Brennan review cycle |
| **07-14 → 08-14** | Optional enhancements (ecological audit, polish) |
| **08-14 → 09-11** | Final preparation + submission |

---

## Mantras

1. **Text-only is king** — cleanest signal, cheapest to run, most sensitive to semantic changes
2. **SSIM > CUA** — mathematical proof of visual equivalence beats noisy agent inference
3. **Smoker first** — never manipulate a task you haven't verified is base-solvable
4. **Operator-centric** — our unit of analysis is the operator (26), not the task (50-100)
5. **Budget is finite** — every dollar on CUA/SoM is a dollar not spent on more tasks
