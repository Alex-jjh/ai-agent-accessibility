# Smoker Shard B — Pre–Stage-3 Trace Audit (2026-05-06)

**Scope**: 109 passing tasks (78 gitlab + 31 reddit) from
`results/smoker/passing-tasks.json`, evaluated against the 930 case
JSONs in `data/smoker-shard-b/dac27420-a4ae-4899-b9e0-daeed23b5c52/cases/`.

**Audit script**: `scripts/smoker/audit-shard-b-trace.py` (committed).

---

## Executive summary

**Recommendation: CONDITIONAL GO on Stage 3 with two fixes (both cheap).**

The gate pipeline is working as advertised. BridgeLogs are clean (zero
context-window / timeout / traceback / login-failed hits across 327
cases), step distribution sits well inside the [3, 25] window, and spot-
checked final answers look coherent against their intents. Reddit's
lower pass rate is substantially explained by infrastructure (`goto_timeout`
= 11.4% reddit vs 0% gitlab) plus the same trivial-task filter that
dropped gitlab equally — not a data-quality cliff we need to fix before
Stage 3.

Two issues do warrant action before we spend the $800:

1. **15 tasks have must_include tokens ≤2 chars** (single digits `'0'`/`'1'`/`'2'`/`'5'`/`'14'` or the 2-char `'Lo'`). On task 306 this already
   false-positives in the smoker itself: two of three reps return long
   prose giving the *wrong numeric answer*, but `"0"` still substring-
   matches because the prose mentions "2023" / "commits". Under
   manipulation this evaluator asymmetry will *suppress* observed drops
   for counting-type tasks. Recommend flagging this subset for
   sensitivity analysis (not dropping).
2. **73% of the passing set (80/109) mutates shared Docker state**
   (issue creation, merge requests, license edits, status updates,
   `url_match` + `program_html` evals). The $800 Stage 3 runs
   26 ops × 3 reps × 2 models = 156 writes per task into a single
   shared GitLab / Postmill instance. Unless the runner resets Docker
   between cells (not documented anywhere I can see), state drift will
   contaminate the signal — the same failure mode that forced Mode A's
   `ground-truth-corrections.json` post-hoc on tasks 41/198/293.

Neither blocks launch if acknowledged. Two-line config changes fix #1
(sensitivity subset) and #2 (re-seed before each cell) if the capability
is already there.

---

## Focus 1: Answer drift in "consistent" passing tasks

**Finding**: 27/109 passing tasks (24.8%) have ≥2 distinct normalized
final answers across 3 reps. BUT this largely reflects the auditor's
deliberate removal of the answer-consistency gate on 2026-05-06 — by
design, BrowserGym's evaluator judges correctness; answer-text paraphrase
isn't a failure. Splitting by eval type:

| Drift sub-category | Count | Impact |
|---|---|---|
| State-mutation (eval uses `program_html` and/or `url_match`) | 24 | **Benign.** Drift is `'done'` vs `<NONE>` vs "done" — DB is authoritative. |
| Info-retrieval (eval uses only `string_match`) | 3 | **Worth inspecting.** |

The 3 info-retrieval drift tasks:

- **`gitlab:306`** — intent "How many commits did Anthony make between
  08/2022-09/2022?" (ref `must_include=['0']`)
  - rep1 (`len=500`): "Anthony Palomarez made 1 commit on January 5,
    2023… From what I can observe in the commit history shown (which
    goes from March…)" — *wrong*, still passes (`'0'` ∈ "2023")
  - rep2 (`len=1`): `"0"` — correct
  - rep3 (`len=259`): "…I can only find one commit by Anthony Palomarez
    from January 5, 2023… Therefore, Anthony made 0 commits between
    08/2022-09/2022." — correct by reasoning
  - **This is a real false positive baseline** driven by the short ref
    token. See Focus 5.
- **`gitlab:350`** — intent "Who else have access to my repo prism-theme"
  (ref `must_include=['abisubramanya27']`)
  - rep1: `'abisubramanya27, byteblaze'`
  - rep2: `'abisubramanya27, byteblaze, yjlou'`
  - rep3: `'@abisubramanya27, @byteblaze'`
  - All contain the ref token; actual answer likely disagrees about `yjlou`.
    Paraphrase, not a data-quality blocker.
- **`reddit:69`** — "is there any post talks about supporting local book
  stores?"
  - Three reps all identify the same post ("Friendly reminder
    bookshop.org exists.") but paraphrase the answer. Benign.

**Verdict**: drift does not invalidate the "consistent" label as used
by the pre-registered gate. Task 306 is a leakage symptom, surfaced more
cleanly in Focus 5. No tasks to drop here.

---

## Focus 2: Hidden bridge errors

**Finding**: Near-zero. Across 327 passing-task bridgeLogs:

| Pattern | Tasks hit |
|---|---|
| `context.*(window|length|exceed)` | 0 |
| `Traceback (most recent call last)` | 0 |
| `ERR_…`, `Error:`, `Exception:` | 0 |
| `TimeoutError` | 0 |
| `login\s+(failed|timeout|error)` | 0 |
| `Playwright.*(Error|closed|crashed|fail)` | 0 |
| `[bridge] … (fail|error|crash)` | **1 (false positive)** |

The one hit is `gitlab:662`, but the substring `"OSError: [Errno 98]
Address already in use"` is **the task intent itself** — "Open an issue
to report experiencing `OSError: [Errno 98] Address already in use`". The
agent is typing it into a form, which our regex then mistakes for a
bridge fail:

> `[bridge] Step 7: executing action: fill("516", "OSError: [Errno 98] Address already in use during executions")`

**Verdict**: the harness is clean on the passing set. Nothing to drop.

---

## Focus 3: Answer quality (intent ↔ final answer)

Spot-check of 10 random passing tasks. All answers plausible for their
intents. Representative examples:

- `gitlab:314` (median 10 steps) — "List the name of the top 3 contributors to prime/design repo":
  all three reps → `'Shawn Allen, Inayaili León, Aurora Pleguezuelo'` ✓
- `gitlab:784` (median 5 steps) — "email address of the contributor
  who has the most commits to branch main":
  all three reps → `'secupwn@users.noreply.github.com'` ✓
- `gitlab:787` (median 3 steps) — "number of followers of the
  contributor who has the most commits to branch main":
  all three reps → `'0'` — *plausible but flagged under Focus 5*
- `gitlab:105` → `'done'` ×3 (state-mutation, program_html eval) ✓
- State-mutation tasks (`421` "Set my status as Resting", `449` "set
  homepage URL", `400` "Change bio") → `<NONE>` ×3.
  Claude emitted `stop()` or a successful mutation without calling
  `send_msg_to_user`. Evaluator is program_html, so the missing message
  is not a correctness issue.

**Verdict**: no obvious hallucination. The `<NONE>` pattern on
state-mutation is normal.

---

## Focus 4: Step distribution

Among the 109 passing tasks:

```
min=3  p25=4.5  median=7  p75=9  max=18
Histogram (rounded median): 3:11  4:16  5:10  6:16  7:19  8:8
                             9:7  10:6  11:4  12:2  13:6  15:1
                             16:1  17:1  18:1
```

| Boundary | Count | Risk |
|---|---|---|
| median_steps ∈ [3, 4] | **27** (24.8%) | Highest manipulation risk: operator may push agent below evaluator's "just got lucky" floor |
| median_steps ∈ [23, 25] | **0** | No step-budget risk |

Low-boundary tasks: `gitlab:132, 133, 136, 173, 175, 176, 207, 305,
593, 665, 787` (median 3); `gitlab:134, 135, 318, 419, 421, 422, 441,
442, 443, 444, 445, 448, 449, reddit:406, 595, 69` (median 4).

These dominate gitlab's "commit-counting" and "set-profile-attribute"
templates. **Not a go/no-go issue** — these tasks are still above the
pre-registered floor, and several (the counting template) are exactly
where L1/L5 manipulation should show the largest relative drop.

**Verdict**: step distribution is clean. The 27 low-boundary tasks
should be reported as "at-risk subset" in the Stage 3 analysis but are
fine to include.

---

## Focus 5: Suspicious patterns

### 5a. Short durations (<15s successful): **0**. Nothing to flag.

### 5b. Empty/null `send_msg_to_user` on success: 99 cases across ~33 tasks

These are all state-mutation tasks (Set status, Make MR, Edit LICENSE, etc.)
with `program_html` eval. Claude correctly performed the mutation and
emitted `stop()` without the user-message wrapper. Benign.

### 5c. Canned answers across different tasks — **REAL ISSUE**

| Answer | # distinct tasks with this as dominant answer |
|---|---|
| `'done'` | 45 |
| `''` (empty) | 33 |
| `'0'` | 6 (`gitlab:134, 305, 787, reddit:27, 30, 31`) |
| `'1'` | 4 (`gitlab:132, 135, 207, 303`) |

`'done'` and empty are by design (state-mutation tasks). The ones that
matter are `'0'` and `'1'` — six tasks whose expected answer and the
pre-registered evaluator token are both the single digit `'0'`.

### 5d. Trivially-short `must_include` tokens — **THE ONE CONCERN**

Cross-referencing `test.raw.json` against the 109 passing tasks,
**15 tasks have a `must_include` token ≤2 characters**:

| Task | must_include | intent |
|---|---|---|
| gitlab:132 | `'1'` | How many commits did kilian make to a11yproject on 3/5/2023? |
| gitlab:133 | `'2'` | How many commits did Eric make to a11yproject on 3/2? |
| gitlab:134 | `'0'` | How many commits did kilian make on 3/1/2023? |
| gitlab:135 | `'1'` | How many commits did Eric and Kilian make on 1/3/2023? |
| gitlab:136 | `'5'` | How many commits did Steven Woodson make on 2/6/2023? |
| gitlab:207 | `'1'` | How many commits did Eric and Kilian make on 1/3/2023 in total? |
| gitlab:303 | `'1'` | How many commits did Kilian make during 2023? |
| gitlab:304 | `'14'` | How many commits did Eric make between Feb-May 2023? |
| gitlab:305 | `'0'` | How many commits did Philip make in 2023/1? |
| gitlab:306 | `'0'` | How many commits did Anthony make between 08/2022-09/2022? |
| gitlab:318 | `'Lo'` | List the last names of the top 3 contributors to 2019-nCov |
| gitlab:787 | `'0'` | Number of followers of the contributor with most commits to main |
| reddit:27  | `'0'` | Count of downvoted comments for the user who made latest Showerthoughts post |
| reddit:30  | `'0'` | …same template, space forum |
| reddit:31  | `'0'` | …same template, photoshopbattles forum |

**Concrete false-positive already seen in the smoker itself** —
`gitlab:306`, ref = `'0'`:

- `gitlab_base_306_0_1.json` (length=500): "Anthony Palomarez made **1**
  commit on January 5, **2023**. However, I need to find commits
  specifically from August-September 2022. From what I can observe…"
  → *states the wrong count (1 ≠ 0)*, still passes because `'0'` appears
  in "2023".
- `gitlab_base_306_0_3.json` (length=259): Claude correctly reasons to
  the right answer ("Anthony made 0 commits between 08/2022-09/2022").
- `gitlab_base_306_0_2.json`: clean `'0'`.

Under manipulation, the expected failure mode for an operator like L1/L5
is "agent over-retries, emits a long confused final message". Those
confused messages will still substring-match `'0'` / `'1'` / `'2'` /
`'Lo'` most of the time → **the evaluator symmetrically under-counts
drops for this 13.8% subset**.

**Recommendation**: don't drop these tasks, but compute Stage 3 drops
both *including* and *excluding* this subset. Report the lower of the
two as the headline. The task-selection methodology document already
frames the gate as "conservative lower bound"; this is one more
conservative-lower-bound caveat, not a blocker.

---

## Focus 6: Reddit vs GitLab pass-rate imbalance

Drop-reason breakdown from `filter-summary.csv`:

| Category | gitlab (n=196) | reddit (n=114) |
|---|---|---|
| **included** | **78 (39.8%)** | **31 (27.2%)** |
| trivial_task | 62 (31.6%) | 26 (22.8%) |
| harness_errors | 35 (17.9%) | 30 (26.3%) |
| stochastic_base | 21 (10.7%) | 14 (12.3%) |
| goto_timeout | 0 (0.0%) | **13 (11.4%)** |

What this says:

- **Trivial-task** is the single biggest bucket on both apps — nearly
  identical in absolute count (62 vs 26 = 31.6% vs 22.8%). This is a
  WebArena property, not a reddit weakness. Non-fixable.
- **Harness errors** are elevated on reddit (26.3% vs 17.9%). Some of
  these are infrastructure (Postmill's more dynamic DOM + BrowserGym
  serialization quirks, per the BrowserGym-divergence finding already in
  project-phases.md Phase 2).
- **Reddit-specific `goto_timeout` (13 tasks, 11.4%)** is pure
  infrastructure — Playwright `Page.goto()` timing out on start_url.
  Most are `reddit:597-617, 630, 648, 720, 725, 730` — a cluster of
  task IDs that share template patterns (subreddit-feed pages). This is
  fixable with a longer `goto` timeout in `browsergym_bridge.py`, but
  it's not contaminating our 109-task set — these were correctly
  filtered out.

**Verdict**: the 12.6pp gap (39.8% − 27.2%) decomposes to roughly
(trivial 8.8pp) + (goto_timeout 11.4pp) − (harness 8.4pp). Reddit's
"loss" is mostly genuine benchmark composition (more short-answer landing
page tasks) plus one tractable infrastructure issue that didn't affect
the gate's 31 included tasks. Not a go/no-go concern.

---

## Additional finding (surfaced during audit): template clustering

109 passing tasks reduce to **40 unique `intent_template_id` values**.
Ten templates account for 51 tasks (47%); the top 5 templates all have
5–6 passing tasks each:

| template | n | sample intent |
|---|---|---|
| gitlab/328 (open issue report) | 6 | "Open an issue to report the issue of connection refused in ChatGPT" |
| gitlab/322 (commit count) | 5 | "How many commits did kilian make to a11yproject on 3/5/2023?" |
| gitlab/323 (top contributor) | 5 | "Who has made the most contributions to the primer/design project?" |
| gitlab/355 (LICENSE edit) | 5 | "Make the LICENSE of byteblaze/cloud-to-butt to MIT license" |
| gitlab/361 (gitlab status) | 5 | "Set my gitlab status as Busy" |
| gitlab/308 (project title) | 5 | "Update the project site's title to 'GIVE ME SPACE'" |
| gitlab/331 (homepage URL) | 5 | "set the homepage URL on my profile to https://egg.tart.com" |
| gitlab/339 (milestone) | 5 | "Create a milestone for product launch from 1/16/2023 to 1/30/2023" |
| gitlab/335 (merge request) | 5 | "Submit a request to merge dialog-component into dialog, assign Carol" |
| reddit/6 (reddit bio) | 5 | "Change my reddit bio to 'I am a robot'" |

**Not a go/no-go issue** — the planned CLMM / GEE analyses use task as
a random effect, which already discounts the pseudo-replication. But
worth noting in the paper and for choosing `N_effective` for power: 109
tasks ≠ 109 independent information units.

---

## Additional finding: state-mutation dominance

**80 of 109 passing tasks (73%)** have an eval with `url_match` or
`program_html` — i.e., success is judged by the state of the Postmill
or GitLab database:

- gitlab: 53 state-mutation tasks (out of 78)
- reddit: 27 state-mutation tasks (out of 31)

These include:
- Opening/closing issues (`gitlab:662, 663, 664, 665, 670`, …)
- Submitting merge requests (`gitlab:666, 667, 805, 806, 807`, …)
- Editing project settings (title, LICENSE, homepage) (`gitlab:308, 355, 411-414`, …)
- Changing user bio/status (`gitlab:361, 418-422, reddit:6`)
- Creating milestones (`gitlab:339`)
- Creating reddit posts (`reddit:13, 6100, 622-640`)

Stage 3 plans 26 ops × 3 reps × 2 models = 156 runs per task. Applied
to the 80 state-mutation tasks, that's **~12,480 mutations** to a
shared Docker instance over the Stage-3 window.

**Known precedent**: Mode A (3,042 cases, 13 tasks) already hit Docker
drift on tasks 41, 198, 293, and ran `ground-truth-corrections.json`
post-hoc. The same risk scales: if the Stage 3 runner does not reset
the Docker volume between cells (or at minimum between reps for a given
task), baseline success will drift downward over the run, and the drift
will be misattributed to later operators.

**Recommendation (the one hard ask from this audit)**: before launching,
confirm one of:

1. The Stage 3 runner already does `env.reset()` + WebArena Docker
   snapshot rollback between cells (documented in `src/runner/scheduler.ts`
   or equivalent).
2. OR restrict Stage 3 *primary* analysis to the **29 info-retrieval
   tasks** (eval=`string_match` only, no state mutation): 25 gitlab +
   4 reddit. State-mutation tasks can still be run as a secondary set
   but flagged with a Docker-drift caveat identical to the Mode A
   `ground-truth-corrections.json` note.

Option 2 is the conservative default and still gives a respectable
N_tasks for the CHI-facing main table. Option 1 is higher-power if the
reset is actually wired.

---

## Suggested remediations, ordered by cost

| # | Action | Cost | Impact |
|---|---|---|---|
| 1 | Before launch: confirm Docker reset is wired per cell. If not, document it; if can't fix in time, run Stage 3 on state-mutation tasks with explicit baseline recomputation (à la Mode A). | 1 hour check | Prevents the most likely contamination source. |
| 2 | Tag the 15 short-`must_include` tasks as "sensitivity subset". Report Stage 3 drops both with and without them. | 0 code (analysis time) | Makes the paper's lower-bound claim defensible under reviewer scrutiny. |
| 3 | Note in `task-selection-methodology.md` §5 that 109 tasks map to 40 templates; main analysis must use task-ID random effect (already planned per CLMM notes). | 15 minutes | Preempts a standard reviewer critique about independence. |
| 4 | *Optional:* raise goto-timeout in `browsergym_bridge.py` for subreddit pages and re-smoker the 13 `reddit:goto_timeout` tasks. | 2–3 hours | Only worth it if Stage-3 reddit N feels tight. |

No tasks need to be dropped from `passing-tasks.json`.

---

## One-line go/no-go

**GO, with a Docker-reset confirmation and a 15-task sensitivity flag.**
Data quality inside the 109-task set is clean (zero hidden bridge
errors, zero step-budget edge cases, coherent answer semantics). The
risks that exist are at the evaluator/environment level, not the trace
level — and both are cheap to mitigate before the $800 run.
