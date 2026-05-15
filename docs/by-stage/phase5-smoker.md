# Phase 5 — Smoker (Base-Solvability Gate, N=2,052)

> **Purpose**: pre-registered upstream gate that filters 684 deployed-app
> WebArena tasks down to the 48 used in Phase 6 Stage 3. Cases are NOT
> reported in any paper success-rate table; the **funnel itself** (684 → 48)
> is reported and cited as the rationale for Stage 3 task selection.
> **Status (2026-05-15)**: data frozen 2026-05-07. Pre-registration locked
> 2026-05-06; gate criteria not changed post-hoc.

## Research conclusions

- **684 → 48 task funnel** via 7 gates: deployment, strict 3/3 base
  solvability, ≥3 / ≤25 median steps, no state mutation, non-trivial
  reference, zero infrastructure failures. Each gate **conservative**
  (drops more, not fewer) → reported drops are lower bounds.
- **48 passing tasks unevenly distributed**: ecommerce 22, ecommerce_admin
  12, gitlab 13, reddit 1. Postmill's high state-sensitivity eliminates
  113/114 reddit tasks at Gate 5.
- **Pre-registration locked 2026-05-06/07** before Stage 3 manipulation
  data collected. Gate standards not fitted post-hoc.
- **Mode A / Stage 3 convergence**: only **5/13** Mode A hand-picked tasks
  pass the *full* 7-gate (Gate 6+7-amended) check (ecom:23, ecom:26,
  gitlab:308, admin:94, admin:95). The 8 that fail are exactly the tasks
  Mode A itself documents as controls: noise-floor (reddit:29, reddit:67),
  operator-immune (gitlab:132, ecom:24, ecom:41, ecom:188), Docker-drift
  (gitlab:293, admin:198), or stochastic baseline (admin:4). Two
  independent selection procedures (April hand-selection vs May 7-gate
  pre-registration) reject the same 8 tasks as unfit for main-effect
  breadth analysis — strong convergence evidence the gate is principled,
  not fitted. (An earlier shard-B-only check claimed 10/13 pass; that
  was superseded by the full shard-A+B re-check on 2026-05-07.)
- **➜ Provides the locked task set for Phase 6 Stage 3** breadth experiment
  and the §4 task-funnel narrative (Figure F11).

## Why this matters (and is its own phase)

Stage 3's 48 tasks aren't a hand-pick — they survive a **7-gate inclusion
protocol** applied to every deployed-app task. The smoker run produces
the data that drives the gate decisions. If we removed it, the entire
breadth claim ("48 tasks pre-registered from a pool of 684") loses its
provenance. Hence: first-class phase, not "support data".

## Design matrix

```
684 tasks (4 deployed apps)  ×  base variant only  ×  text-only  ×  3 reps
```

| Dimension | Values |
|---|---|
| Tasks | All 684 tasks across 4 deployed WebArena apps. Sources: shopping_admin (182), shopping (192), reddit (114), gitlab (196). Map (128) and wikipedia (16) excluded — not deployed in our infra. |
| Variant | base only (control). The point is "is the task solvable at all?" |
| Agent × Model | Claude × text-only (single cell — cheapest, fastest sanity baseline) |
| Reps | 3 |

## On-disk data (~1.7 GB total)

| Directory | Cases | Apps | Date |
|---|--:|---|---|
| `data/smoker-shard-a/` | 1,122 | shopping_admin (182) + shopping (192) | 2026-05-06 |
| `data/smoker-shard-b/` | 930 | reddit (114) + gitlab (196) | 2026-05-06 |
| **Total** | **2,052** | | |

Sharded by app to parallelise across two burner accounts.

## The 7 gates

| # | Gate | Purpose | Reduction |
|---|---|---|---|
| 1 | App deployed | exclude map + wikipedia | 812 → 684 |
| 2 | Strict 3/3 base solvability | reject stochastic/flaky tasks | varies |
| 3 | ≥3 median steps | reject trivial tasks | |
| 4 | ≤25 median steps | reject overly long tasks (timeout risk) | |
| 5 | No state mutation | reject tasks that change Docker DB | |
| 6 | Non-trivial reference answer | reject empty/template-only answers | |
| 7 | Zero infrastructure failures | reject tasks affected by 5xx, network, anti-bot | |

Each gate is **conservative** (drops more tasks, not fewer), so the
reported drop per operator is a lower bound. Gate criteria are
documented in `docs/analysis/task-selection-methodology.md`.

## Derived artefacts (`results/smoker/`)

| File | Schema |
|---|---|
| `results/smoker/passing-tasks.json` | `{app: [taskId, ...]}` for the 48 surviving tasks |
| `results/smoker/passing-tier2.json` | tier-2 tasks (lower confidence, not used in Stage 3) |
| `results/smoker/filter-summary.csv` | per-task gate verdicts |
| `results/smoker/exclusion-report.md` | paper-ready narrative of the 636 dropped tasks |

Headline counts (paper §4 + Figure F11 funnel):
- 684 candidate tasks
- 258 base-stochastic (Gate 2 fails) → tier-2 reference
- 48 passing all 7 gates → Stage 3 set
  - ecommerce: 22
  - ecommerce_admin: 12
  - gitlab: 13
  - reddit: 1

## How to audit

```sh
make audit-smoker
```

Verifier asserts:
- shard A case count = 1,122; shard B = 930; total = 2,052
- `passing-tasks.json` total = 48
- per-app passing counts (22 / 12 / 13 / 1) match `_constants.SMOKER_PASSING_BY_APP`
- exactly 4 apps in the JSON

## Paper sections

- **§4 Methodology — Task selection** — the 7-gate funnel + exclusion narrative
- **Figure F11 (`F11_task_funnel.png`)** — funnel diagram 684 → 48
- **`docs/analysis/task-selection-methodology.md`** — full pre-registration text

## Convergence with Mode A

Retrospective check (full 7-gate, shard A + B, 2026-05-07): **5 of 13 Mode A
tasks pass** all gates (ecom:23, ecom:26, gitlab:308, admin:94, admin:95).
The 8 that fail are exactly the tasks Mode A's own documentation classifies
as controls:
- `reddit:29`, `reddit:67` — noise-floor / stochasticity controls
- `gitlab:132`, `ecom:24`, `ecom:41`, `ecom:188` — operator-immune controls
- `gitlab:293`, `admin:198` — Docker-drift (GT-corrected in Mode A)
- `admin:4` — genuine stochastic baseline

Two independent selection procedures (April hand-selection for Mode A vs
May 7-gate pre-registration for Stage 3) reject the same 8 tasks as
unfit for main-effect breadth analysis. **This is a stronger convergence
statement than picking-out-the-failures**: every formal-gate failure has
an independent prior justification documented in Mode A.

Earlier shard-B-only check (2026-05-07 AM) reported 10/13; that was
superseded by the full shard-A+B re-check the same day after Gate 6+7
were added (see `docs/analysis/task-selection-methodology.md` §8.1).

This convergence between manual (Mode A) and formal (Stage 3) selection
is reported in §4 as evidence the gate is principled rather than fitted.

## Known caveats

- **Single rep × single agent × single variant**. Cannot draw any
  per-operator conclusion from the smoker — it's a solvability gate only.
- **Reddit yields just 1 passing task** out of 114. This is an artefact of
  Postmill's high state-sensitivity (most tasks involve creating/voting),
  not a bug. Documented in §6 Limitations.
- **Pre-registration is locked**. Re-running the smoker with relaxed
  criteria post-hoc would be cherry-picking; the 48-task set is frozen.
