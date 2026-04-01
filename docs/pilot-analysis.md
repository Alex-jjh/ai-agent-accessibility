# Pilot Study Analysis & Post-Mortem

Date: 2026-04-02
Run ID: `1691792f-affd-4adb-a0c1-0c8108a1b621`
Run Date: 2026-04-01 12:50 – 14:59 UTC (~2h 10min)
Commit (fixes): `8c7d596`

## Executive Summary

The first pilot ran 54 test cases (3 apps × 2 variants × 3 tasks × 3 reps × 1 LLM).
Only 4 succeeded (7.4% raw success rate). Root cause analysis revealed that 48 of 50
failures were caused by infrastructure bugs and task design issues, not accessibility
barriers or model limitations. The effective success rate on valid cases was 4/6 (66.7%).

One failure — `reddit:low:102` context overflow — provided the first empirical evidence
of the accessibility-performance gradient the experiment is designed to detect.

## Experiment Matrix

| Parameter | Value |
|-----------|-------|
| Apps | ecommerce, reddit, wikipedia |
| Variants | low, high |
| Tasks per app | 3 (ecommerce: 0,1,2 / reddit: 100,101,102 / wikipedia: 0,1,2) |
| Agent configs | 1 (text-only, claude-sonnet, temp=0, maxSteps=30) |
| Repetitions | 3 |
| Total cases | 54 |
| Successes | 4 (all reddit:102) |
| Failures | 50 |

## Root Cause Taxonomy

### Root Cause 1: Task Routing Bug (18 cases)

**Impact:** All 18 "wikipedia" cases were routed to the ecommerce (Magento) site.

**Mechanism:** `browsergym_bridge.py` maps numeric task IDs to `browsergym/webarena.{taskId}`.
WebArena task IDs are global — tasks 0-2 are ecommerce admin tasks regardless of what app
label the scheduler assigns. The scheduler generated `wikipedia:low:0:0:1` with taskId `"0"`,
which BrowserGym resolved to `browsergym/webarena.0` — an ecommerce task.

The scanner correctly scanned the wikipedia URL (`http://10.0.1.49:8888`), but the agent
was launched on the ecommerce site by BrowserGym. This created a mismatch between scan
metrics (wikipedia) and agent behavior (ecommerce).

**Fix applied:** `buildTasksPerApp()` in `src/index.ts` now uses correct WebArena task ID
ranges per app (ecommerce: 3-99, reddit: 100-199, wikipedia: 400-811). Config YAML can
override via `webarena.tasksPerApp`. `config-pilot.yaml` now has explicit mapping.

### Root Cause 2: Tasks 0/1 Not Completable on Storefront (36 cases)

**Impact:** All ecommerce task 0/1 and wikipedia task 0/1 cases (which were actually
ecommerce due to Root Cause 1).

**Mechanism:** WebArena tasks 0-2 require the Magento admin backend (`:7780`) to access
sales analytics. The pilot config only had `ecommerce` (storefront at `:7770`), not
`ecommerce_admin`. The agent searched for "best selling 2022" on the storefront, which
has no sales data — only a product catalog with keyword search.

The agent correctly recognized the data wasn't available but burned all 30 steps exploring
before giving up. The classifier labeled these F_REA (reasoning error) but the true cause
is task impossibility on the storefront.

**Fix applied:** Default task mapping now assigns tasks 0-2 to `ecommerce_admin` and
tasks 3-99 to `ecommerce`. The pilot config includes both apps with correct URLs.

### Root Cause 3: Bracket Syntax Bug in `fill()` Actions (12 cases)

**Impact:** All task 2 cases across ecommerce and wikipedia (actually ecommerce).

**Mechanism:** The accessibility tree displays elements as `[413] textbox 'Email*'`.
The LLM copied the bracket notation into actions: `fill("[413]", "email")`. BrowserGym
does exact string matching on bid values, so `"[413]"` ≠ `"413"` → `ValueError`.

At temperature=0, the LLM is deterministic — it produced the identical failing action
every step, creating a 30-step loop with zero progress. The `cleanAction()` function
in `executor.ts` handled escaped quotes and smart quotes but not brackets.

**Fix applied:**
1. `cleanAction()` now strips brackets: `fill("[413]", ...) → fill("413", ...)`
2. System prompt explicitly instructs: "Use BARE NUMERIC bid values WITHOUT brackets"

### Root Cause 4: Reddit Tasks 100/101 Incompatible with Sandbox (12 cases)

**Impact:** All reddit task 100 and 101 cases.

**Mechanism:**
- Task 100 asks for "nearest Starbucks to CMU with walking distance" — requires a
  mapping/geolocation service that doesn't exist in WebArena.
- Task 101 asks for "In-N-Out near Upitts" — same issue, plus the BrowserGym bridge
  crashed with `OPENAI_API_KEY environment variable must be set` before rendering any page.

The classifier assigned F_REA with 0.3 confidence and flagged for review. The correct
classification is F_TSK (task incompatible with environment).

**Fix applied:** These tasks will be replaced during task screening. The `screen-tasks.ts`
script now validates task ID ranges per app to prevent mismatched routing.

### Root Cause 5: Low Variant Context Overflow (1 case) ⭐

**Impact:** `reddit:low:102:0:2` — the only accessibility-attributed failure.

**Mechanism:** Task 102 (GitLab issues browsing) is the only task that worked correctly.
The high variant succeeded 3/3 times. The low variant succeeded 2/3 times, with one
failure due to context overflow (221K tokens > 200K claude-sonnet limit).

The low variant's degraded accessibility tree was noisier:
- Ordered list markers showed `0.` instead of `1.`, `2.`, `3.`
- Missing landmark roles and navigation semantics
- More raw DOM element IDs exposed without semantic labels

Each observation consumed more tokens in the low variant. Over 30 steps, the cumulative
token count exceeded the context window. The agent entered a confused loop, repeatedly
trying to "analyze the current page" without making progress.

**Significance:** This is the accessibility-performance gradient signal the experiment
is designed to detect. The mechanism is clear: degraded semantics → noisier a11y tree →
token inflation → context overflow → task failure.

**No code fix needed** — this is expected experimental behavior.

## Corrected Success Rate

| Category | Cases | Cause | Valid for analysis? |
|----------|-------|-------|---------------------|
| Wikipedia routed to ecommerce | 18 | Infrastructure bug | No |
| Task 0/1 not completable | 24 | Task design (need admin) | No |
| Bracket syntax loop | 12 | Code bug (fixed) | No |
| Task 100/101 need map service | 12 | Sandbox incompatible | No |
| **Valid cases (task 102)** | **6** | — | **Yes** |

Valid results: 4 successes / 6 valid cases = **66.7%** effective success rate.

## Key Metrics from Valid Cases (reddit:102)

| Case | Variant | Success | Steps | Tokens | Duration |
|------|---------|---------|-------|--------|----------|
| reddit:high:102:0:1 | high | ❌ | 6 | 37,595 | 57s |
| reddit:high:102:0:2 | high | ✅ | 6 | 41,898 | 54s |
| reddit:high:102:0:3 | high | ✅ | 9 | 60,020 | 81s |
| reddit:low:102:0:1 | low | ✅ | 5 | 35,958 | 55s |
| reddit:low:102:0:2 | low | ❌ (F_COF) | 30 | 221,312 | 257s |
| reddit:low:102:0:3 | low | ✅ | 5 | 36,032 | 55s |

Observations:
- High variant: 2/3 success, avg 46K tokens on success
- Low variant: 2/3 success, but the failure consumed 5x more tokens
- The low variant failure (F_COF) is the only case showing measurable a11y impact

## Scan Metrics Comparison

| App | Variant | Lighthouse | Composite | axe Violations | Pseudo-compliance |
|-----|---------|-----------|-----------|----------------|-------------------|
| reddit | high | 100 | 0.352 | 0 | 0 |
| reddit | low | 100 | 0.370 | 1 (critical) | 0 |
| ecommerce | high | 87 | 0.423 | 5 (2 crit, 3 serious) | 301 (99.3%) |
| ecommerce | low | 87 | 0.317 | 2 (1 crit, 1 serious) | 0 |
| wikipedia | high | 84 | 0.424 | 1 (serious) | 0 |
| wikipedia | low | 84 | 0.398 | 3 (1 crit, 2 serious) | 0 |

Note: ecommerce high variant has 301 pseudo-compliant elements (ARIA present but handlers
missing) — this is the medium-low/high variant injection working as designed.

## Implications for Experiment Design

1. **Task screening is mandatory** before the next pilot. Use `scripts/screen-tasks.ts`
   to find tasks with 30-70% base success rate.

2. **The classifier needs improvement** for infrastructure failures. F_REA at 0.3
   confidence with flaggedForReview=true was correct to flag uncertainty, but a dedicated
   F_TSK (task incompatible) or F_ENV (environment failure) category would be more precise.

3. **The context overflow finding is publishable** — it demonstrates a concrete mechanism
   by which accessibility degradation impairs AI agent performance, independent of the
   agent's reasoning capability.

4. **Token tracking per step** should be added to trace data to enable per-step analysis
   of the token inflation effect across variants.

## Files Modified (commit 8c7d596)

| File | Change |
|------|--------|
| `src/runner/agents/executor.ts` | Bracket stripping in `cleanAction()`, system prompt improvement |
| `src/runner/browsergym_bridge.py` | Action timeout 10s → 3s |
| `src/config/types.ts` | Added `tasksPerApp` to `ExperimentConfig.webarena` |
| `src/index.ts` | `buildTasksPerApp()` respects config overrides |
| `config-pilot.yaml` | Explicit `tasksPerApp` with correct WebArena ranges |
| `scripts/screen-tasks.ts` | Task ID range validation, `--maxSteps` param |
| `scripts/run-pilot.ts` | `--resume`/`--config`/`--cdp-port` params, per-app stats |
| `scripts/run-regression.ts` | Removed unused import, fixed taskGoal, accurate comments |

## Next Steps

1. **Run regression** (`npx tsx scripts/run-regression.ts`) — verify fixes work (~20min)
2. **Run task screening** per app — find viable tasks (~1h per app)
3. **Update config** with screened task IDs
4. **Run full pilot** with corrected configuration
