# Paper Numbers Audit Architecture

## Design Philosophy

Every quantitative claim in the paper must be **reproducible from raw case
JSON files** in a single command. No intermediate CSVs, no manual calculations,
no "I computed this in a notebook and copied the number."

```
Raw case JSON → audit script → PASS/FAIL per claim
```

## The Audit Chain

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: RAW DATA (immutable, gitignored, S3-backed)           │
│                                                                  │
│  data/mode-a-shard-a/*/cases/*.json   (1,638 Claude cases)      │
│  data/mode-a-shard-b/*/cases/*.json   (1,404 Claude cases)      │
│  data/mode-a-llama4-textonly/*/cases/*.json  (1,014 Llama cases) │
│  data/c2-composition-shard-a/*/cases/*.json  (1,094 C.2 cases)  │
│  data/c2-composition-shard-b/*/cases/*.json  (1,090 C.2 cases)  │
│                                                                  │
│  Each JSON contains: caseId, trace.success, trace.steps,         │
│  trace.agentConfig.observationMode, trace.totalTokens            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: AUDIT SCRIPT (git-tracked, deterministic)             │
│                                                                  │
│  scripts/audit-paper-numbers.py                                  │
│                                                                  │
│  - Reads raw JSON directly (zero intermediate file dependency)   │
│  - GT corrections INLINE (no external file needed)               │
│  - Computes every statistic from scratch                         │
│  - Asserts each against expected value with tolerance            │
│  - Exit 0 = all pass, Exit 1 = failure detected                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: FIGURE SCRIPTS (git-tracked, regenerable)             │
│                                                                  │
│  scripts/amt-signature-analysis.py → results/amt/*.csv           │
│  figures/generate_F4_behavioral_drop.py → F4.png/pdf             │
│  figures/generate_F5_dom_heatmap.py → F5.png/pdf                 │
│  figures/generate_F6_alignment_scatter.py → F6.png/pdf           │
│  figures/generate_F7_cross_model.py → F7.png/pdf                 │
│  figures/generate_F8_composition.py → F8.png/pdf                 │
│  figures/generate_F9_task_heatmap.py → F9.png/pdf                │
│                                                                  │
│  Each reads from results/amt/*.csv (Layer 2.5) or raw JSON       │
│  F8 has hardcoded data (from C.2 analysis, verified by Layer 2)  │
│  F9 reads raw JSON directly (same logic as audit script)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: PAPER MANUSCRIPT (LaTeX, references Layer 3 outputs)  │
│                                                                  │
│  Every number in §4-§5 has a corresponding check() in Layer 2   │
│  Every figure references a specific generate_F*.py script        │
│  Every table can be regenerated from results/amt/*.csv           │
└─────────────────────────────────────────────────────────────────┘
```

## What the Audit Verifies

### §4 Method (case counts)
| Claim | Check | Source |
|-------|-------|--------|
| 3,042 Claude cases | `len(claude_cases) == 3042` | glob count |
| 1,014 per agent | `len(text/som/cua) == 1014` | agent filter |
| 26 operators × 13 tasks × 3 agents × 3 reps | implied by 3042 | |
| GT corrections: 327 cases reclassified | correction count | answer matching |

### §5.1 Per-Operator Results
| Claim | Check | Source |
|-------|-------|--------|
| H-baseline = 93.8% (text) | `h_text_rate ≈ 93.8` | H-op average |
| L1 = 53.8% (−40pp) | `op_rate("L1") ≈ 53.8` | per-op filter |
| L5 = 71.8% (−22pp) | `op_rate("L5") ≈ 71.8` | per-op filter |
| L11 = 92.3% (−1.5pp) | `op_rate("L11") ≈ 92.3` | per-op filter |
| L6 = 100% (−6.2pp) | `op_rate("L6") == 100` | per-op filter |
| Ranking: L1 > L5 > L12 | rate comparison | sorted |

### §5.2 Signature Alignment
| Claim | Check | Source |
|-------|-------|--------|
| L1 Llama drop = 32.6pp | `h_llama - op_rate_llama("L1") ≈ 32.6` | Llama data |
| L11 Llama drop = 14.6pp | `h_llama - op_rate_llama("L11") ≈ 14.6` | Llama data |
| L5 Llama drop = 22.3pp | `h_llama - op_rate_llama("L5") ≈ 22.3` | Llama data |

### §5.3 Cross-Model
| Claim | Check | Source |
|-------|-------|--------|
| L1 and L5 are top-2 for both models | set comparison | sorted drops |

### §5.4 Composition
| Claim | Check | Source |
|-------|-------|--------|
| 15 super-additive pairs | interaction > +5pp | pair computation |
| 9 additive pairs | |interaction| ≤ 5pp | pair computation |
| 4 sub-additive pairs | interaction < −5pp | pair computation |
| L6+L11 interaction = +24pp | specific pair check | pair computation |

## Ground Truth Corrections

Three tasks have Docker data drift (documented in `scripts/amt/ground-truth-corrections.json`):

| Task | Original GT | Additional Valid | Reason |
|------|-------------|-----------------|--------|
| 41 | "hollister" | "abomin", "abdomin" | Agent searches mutated Magento DB |
| 198 | "Lily Potter" | "Veronica Costello" | Order table reindexed |
| 293 | CMU hostname | 10.0.1.50 URL | GitLab reconfigure changed external_url |

The audit script applies these corrections INLINE (no external file dependency)
to ensure the script is fully self-contained.

## How to Run

```bash
# Full audit (reads ~6,200 JSON files, takes ~30s)
python3.11 scripts/audit-paper-numbers.py

# Expected output: "28 passed, 0 failed"
# If any check fails: exit code 1 + ❌ markers showing expected vs actual
```

## When to Re-Run

Run the audit:
1. **Before submitting the paper** — final sanity check
2. **After any change to GT corrections** — ensures consistency
3. **After any change to analysis scripts** — ensures figures match claims
4. **After downloading new data from S3** — ensures data integrity

## Discrepancy Resolution

If the audit fails:
1. **The audit script is the source of truth** (it reads raw data)
2. Update the paper/report numbers to match the audit output
3. Never change the audit to match the paper — that defeats the purpose
4. Document any discrepancy in `docs/analysis/mode-a-docker-confounds.md`

## Relationship to Figure Scripts

The figure scripts (F4-F9) read from `results/amt/*.csv` which is generated
by `scripts/amt-signature-analysis.py`. This creates a dependency:

```
Raw JSON → amt-signature-analysis.py → results/amt/*.csv → generate_F*.py → figures
```

The audit script bypasses this chain and reads raw JSON directly. If the
figures show different numbers than the audit, the bug is in
`amt-signature-analysis.py` (the intermediate step), not in the raw data.

## Future: CI Integration

When the paper repo moves to a CI system, add:
```yaml
# .github/workflows/audit.yml
- run: python3.11 scripts/audit-paper-numbers.py
```
This ensures no PR can merge if paper numbers are inconsistent with data.
