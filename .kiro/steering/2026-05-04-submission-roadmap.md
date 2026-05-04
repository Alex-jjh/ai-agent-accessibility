---
inclusion: auto
---

# CHI 2027 Submission Roadmap — Phase C (Paper Writing)

> **Created**: 2026-05-04
> **Deadline**: 2026-09-11 (CHI 2027 submission)
> **Days remaining**: ~130
> **Status**: All experiments complete. Paper draft v1 done. Now in polish + review cycle.

---

## Current State

### Experiments — ALL COMPLETE ✅

| Phase | Cases | Status |
|-------|-------|--------|
| Composite variant study | 1,040 | ✅ Analyzed, GT-corrected |
| Mode A individual operators (Claude) | 3,042 | ✅ Analyzed, GT-corrected |
| Mode A cross-model (Llama 4) | 1,014 | ✅ Analyzed, GT-corrected |
| C.2 Compositional (28 pairs) | 2,188 | ✅ Analyzed, GT-corrected |
| **Total** | **7,284** | |

No new experiments planned. Budget spent: ~$5,000-6,000.

### Paper — DRAFT V1 COMPLETE ✅

- **Repo**: `github.com/Alex-jjh/ai-accessibility-paper` (master branch)
- **Local**: `../paper/` (sibling to main repo)
- **Pages**: 25 (needs compression to ~12 + refs + appendix)
- **Compiles**: clean, 0 errors, 0 undefined references
- **Figures**: 9 (F1-F9) + 3 retained old figures
- **References**: 18 new citations added for AMT v8
- **Appendix**: 6 sections (majority-vote, architecture, operators, excluded ops, severity mapping, F_UNK review, pseudocode, DOM signature table)

### Analysis — ALL COMPLETE ✅

- 25 statistical procedures across 3 phases (see `docs/statistical-methods-inventory.md`)
- `scripts/amt/audit-paper-numbers.py`: 28/28 paper numbers verified
- `analysis/amt_statistics.py`: Fisher + GEE + majority-vote + Breslow-Day + composition
- Power analysis: 93.4% power for 20pp drop at α=0.05

### Reviews — 5 ROUNDS COMPLETE ✅

5 rounds of AI reviewer simulation (4× ChatGPT, 1× Claude). All actionable items addressed:
- Power analysis added
- Operator derivation rationale added
- Alignment thresholds quantified
- Sparsity tension addressed
- Ethics paragraph added
- BrowserGym dependency caveat added
- Injection vs native-absence limitation added
- Enhancement ceiling explained
- Operator ordering justified
- Same Barrier → "structurally analogous" (softened)
- Ecological "validation" → "probe" (honest)

---

## Roadmap to Submission

### Phase 1: Verification (this week, 05-04 → 05-10)

| Task | Owner | Time | Status |
|------|-------|------|--------|
| Screenshot audit (L1/L5/L6/L11 before/after) | Alex | 30 min | ⬜ |
| Send PDF + change summary to Brennan | Alex | 15 min | ⬜ |
| Run `audit-paper-numbers.py` final check | Kiro | 5 min | ⬜ |
| Run `amt_statistics.py` final check | Kiro | 5 min | ⬜ |

### Phase 2: Compression (05-10 → 05-24)

Target: 25 pages → ~12 pages body + refs + appendix/supplementary.

| Task | Strategy | Est. savings |
|------|----------|-------------|
| §2 Related Work | Compress 7 subsections → 4-5, cut verbose descriptions | 1-1.5 pages |
| §5.1 Composite results | Condense (this is old data summary, not new contribution) | 0.5 page |
| §5.6-5.8 (triangulation, vision, failure) | Tighten prose, move failure table to appendix | 1 page |
| §6 Discussion | Cut redundancy with §5, tighten AI-readiness discussion | 1 page |
| Abstract | Reduce to 3 core messages, cut specific stats | 0.3 page |
| Move to supplementary: DOM sig table, pseudocode, full failure table | — | 1-2 pages |

### Phase 3: Polish (05-24 → 06-14)

| Task | Owner | Notes |
|------|-------|-------|
| Figure readability check (print PDF, verify ≥7pt fonts) | Alex | F1 teaser may need simplification |
| Consistent terminology pass (Claude/Llama 4 short forms, Tier 1/2/3) | Kiro | Find-and-replace |
| Citation format check (no orphan brackets, consistent style) | Kiro | |
| Supplementary materials package | Kiro | Operator code, CSVs, audit script, screenshot guide |
| Anonymization check (if CHI 2027 is double-blind) | Alex | Check CHI 2027 submission guidelines |

### Phase 4: Brennan Review (06-14 → 07-14)

| Task | Owner | Notes |
|------|-------|-------|
| Brennan reads full draft | Brennan | Allow 2-4 weeks |
| Incorporate Brennan feedback | Alex + Kiro | Focus on framing, not data |
| Second round if needed | Brennan | 1 week turnaround |

### Phase 5: Optional Enhancements (07-14 → 08-14)

These are NOT required for submission but would strengthen the paper if time permits:

| Task | ROI | Cost | Notes |
|------|-----|------|-------|
| Expand ecological audit to 100+ sites | HIGH | 1-2 days | Tranco Top 1000, public pages only, axe-core scan |
| CUA trace deep-dive (5-10 cases) | MEDIUM | 3-4 hours | Understand why CUA baseline is 48.2% in Mode A |
| Per-task L1 breakdown figure | MEDIUM | 1 hour | Addresses Q4 from Claude reviewer |
| Mediation analysis (token inflation) | LOW | 2 hours | Formal test of token inflation as mediator |

### Phase 6: Final Preparation (08-14 → 09-11)

| Task | Owner | Deadline |
|------|-------|----------|
| LaTeX format: switch to `[manuscript, screen, review]` | Kiro | 09-01 |
| Check CHI 2027 specific template requirements | Alex | 09-01 |
| Final number audit (`audit-paper-numbers.py`) | Kiro | 09-05 |
| Final compilation + PDF check | Kiro | 09-08 |
| Upload to submission system | Alex | 09-10 |
| **DEADLINE** | — | **09-11** |

---

## Key Decisions Still Open

| Decision | Deadline | Owner |
|----------|----------|-------|
| Paper title: keep "Same Barrier, Different Signatures" or change? | 07-01 | Alex + Brennan |
| CHI 2027 double-blind? Check submission guidelines | 06-01 | Alex |
| Expand ecological audit? (34 → 134 sites) | 07-14 | Alex (cost/benefit) |
| Amazon internship acknowledgment wording | 08-01 | Alex |

---

## Reviewer Concern Tracker

All concerns from 5 rounds of AI review, with resolution status:

| Concern | Rounds | Resolution | Status |
|---------|--------|------------|--------|
| 13 tasks too few | R1-R5 | Power analysis + operator-centric design argument | ✅ |
| Post-hoc alignment | R1-R5 | Labeled exploratory in §3.4 + §6.1 + quantitative thresholds | ✅ |
| 34-site audit thin | R1-R5 | Renamed "ecological probe" + expansion optional | ✅ |
| CUA baseline 48.2% | R3-R5 | Sub-analysis done, explained in §6 Limitations | ✅ |
| 2 model families | R2-R5 | Framed as demonstrations in §6 | ✅ |
| Provider non-determinism | R1,R4 | Majority-vote sensitivity + 11.8% variance cells | ✅ |
| Same Barrier unproven | R5 | Softened to "structurally analogous" + hypothesis framing | ✅ |
| Operator selection rationale | R5 | Systematic Ma11y derivation in §3.1 | ✅ |
| Sparsity vs infrastructure tension | R5 | Directly addressed in §5.2 | ✅ |
| Injection vs native absence | R5 | Limitation added in §6 | ✅ |
| Enhancement ceiling = WebArena artifact? | R5 | Acknowledged + Llama 4 shows effect | ✅ |
| Ethics/safeguards | R2,R4 | 3 risk categories + mitigation in §6 | ✅ |
| BrowserGym dependency | R3,R4 | Caveat in §6 Limitations | ✅ |
| Operator ordering bias | R4 | Canonical ordering justified in §4 | ✅ |
| Human study needed | R1-R5 | Future Work §7 | ✅ (deferred) |
| More models needed | R2-R5 | Future Work / revision | ✅ (deferred) |
| Dynamic injection | R2-R3 | Future Work §7 | ✅ (deferred) |

---

## File Reference

| File | Purpose |
|------|---------|
| `paper/main.tex` | Main LaTeX file |
| `paper/sections/*.tex` | 8 section files |
| `paper/references.bib` | Bibliography (1,500+ lines) |
| `paper/F*.png` | AMT figures (F1-F9) |
| `paper/figure*.png` | Retained old figures |
| `docs/statistical-methods-inventory.md` | 25 statistical procedures |
| `docs/screenshot-audit-guide.md` | Human reviewer guide for visual audit |
| `scripts/amt/audit-paper-numbers.py` | Reproducibility audit (28 checks) |
| `analysis/amt_statistics.py` | All inferential statistics |
| `results/amt/*.csv` | DOM signatures, behavioral signatures, alignment |
