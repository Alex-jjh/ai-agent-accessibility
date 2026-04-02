# Bug Fix Report — 2026-04-02 Round 5

Regression analysis after Pilot 1. Identified 4 platform bugs + 3 agent/evaluator
issues. All platform bugs fixed. Agent issues addressed with prompt tuning and
defensive sanitization.

Commits: `ac2e763`, `9af80dd`, `f0d2897`, `e78fc66`, `30b8cf7`

## Platform Bugs Fixed

### Bug 12 [P2]: lastReward not captured on send_msg_to_user break

**File:** `src/runner/agents/executor.ts`

**Root cause:** When the agent terminates via `send_msg_to_user`, the executor breaks
out of the step loop before capturing `obs.reward`. The `lastReward` variable stays
at its initial value of 0. If BrowserGym returns `reward > 0` on the same step
(ground truth success), `determineOutcome` never sees it.

**Impact:** Tasks where BrowserGym judges success but the agent self-reports via
`send_msg_to_user` (without saying "done") are misclassified as `partial_success`
or `failure` instead of `success`.

**Fix:** Added `lastReward = obs.reward` before the `send_msg_to_user` break.

### Bug 13 [CRITICAL]: WebArena task ID mapping completely wrong

**Files:** `config-pilot.yaml`, `config-regression.yaml`, `src/index.ts`,
`scripts/run-regression.ts`, `scripts/screen-tasks.ts`, `.kiro/steering/project-context.md`

**Root cause:** The steering doc and all code assumed WebArena task IDs are assigned
in contiguous ranges per site (e.g. `reddit: 100-199`, `wikipedia: 400-811`). This
is completely wrong. Task IDs in `webarena/test.raw.json` are **interleaved** across
sites — the same numeric range contains tasks for multiple different apps.

Actual mapping from `test.raw.json`:
```
shopping_admin: 182 tasks, first IDs: 0,1,2,3,4,5,6,11,12,13
shopping:       192 tasks, first IDs: 21,22,23,24,25,26,47,48
reddit:         114 tasks, first IDs: 27,28,29,30,31,66,67,68
gitlab:         196 tasks, first IDs: 44,45,46,102,103,104,105
wikipedia:       16 tasks, first IDs: 265,266,267,268,424,425
map:            128 tasks (NOT DEPLOYED)
```

**Impact:** Pilot 1 and Regression v1 routed agents to wrong websites:
- "reddit" tasks 100-102 → actually map (100,101) and gitlab (102)
- "wikipedia" tasks 400-402 → actually reddit
- "ecommerce" tasks 3-5 → actually shopping_admin

This explains bridge crashes (map service not deployed) and unexpected page content.

**Fix:** Replaced all hardcoded task ID ranges with verified IDs from `test.raw.json`.
Updated configs, code defaults, regression script, screen-tasks validation, and
steering documentation.

### Bug 14 [P1]: BrowserGym 500ms action timeout hardcoded in functions.py

**File:** BrowserGym installed package at
`~/.local/lib/python3.11/site-packages/browsergym/core/action/functions.py`

**Root cause:** BrowserGym hardcodes `timeout=500` in every Playwright action call
(click, fill, hover, press, focus, clear, dblclick, select_option, check, uncheck).
Our `page.set_default_timeout(3000)` has no effect because the explicit `timeout=500`
parameter overrides the default. Magento on t3a.xlarge needs more than 500ms.

Additionally, BrowserGym uses `inspect.getsource()` + `exec()` to execute actions,
so monkey-patching the module-level functions in our bridge has no effect — BrowserGym
reads the source text, not the function references.

**Impact:** ~40% of click actions on Magento pages fail with `Timeout 500ms exceeded`
even though the element exists and is interactable.

**Fix:** Direct `sed` replacement in the installed package:
```bash
sed -i 's/timeout=500/timeout=3000/g' \
  ~/.local/lib/python3.11/site-packages/browsergym/core/action/functions.py
```
This must be re-applied after any BrowserGym reinstall. Added to `scripts/ec2-setup.sh`.

**Regression v3 confirmed:** Only 1 timeout (at 3000ms) across 9 cases, vs ~15
timeouts (at 500ms) in v1/v2.

### Bug 15 [P1]: All Wikipedia tasks require map service (not deployed)

**Discovery:** All 16 wikipedia tasks in `test.raw.json` have
`sites=['wikipedia', 'map']`. BrowserGym's `env.reset()` attempts to initialize
both sites. Map service (port 3000) is not deployed on the WebArena EC2, causing
the bridge to crash with navigation timeout.

**Impact:** Wikipedia tasks are unusable without deploying the map Docker container.

**Fix:** Excluded wikipedia from `config-pilot.yaml`, `config-regression.yaml`, and
`scripts/run-regression.ts`. Documented as known limitation. Can be re-enabled if
map container is deployed in the future.

## Agent/Evaluator Improvements

### Improvement 1: System prompt — concise answer guidance

**File:** `src/runner/agents/executor.ts`, `buildSystemPrompt()`

Agent was outputting long explanatory paragraphs in `send_msg_to_user()`, causing:
- BrowserGym `exec()` failures from internal quotes/newlines
- WebArena evaluator mismatches (expects concise answers)

Added explicit instructions:
```
When the task asks for information, respond with ONLY the direct answer:
  send_msg_to_user("Luma")
  send_msg_to_user("$25.99")
  send_msg_to_user("3")
Do NOT include long explanations. Do NOT use quotes inside the answer text.
```

### Improvement 2: send_msg_to_user sanitization in cleanAction

**File:** `src/runner/agents/executor.ts`, `cleanAction()`

Added defensive sanitization for `send_msg_to_user` action strings:
- Replace internal double quotes with single quotes (prevents Python string breakage)
- Remove newlines (prevents `exec()` parse errors)
- Truncate to 500 chars (prevents token explosion in BrowserGym)

This catches cases where the agent ignores the prompt guidance and still outputs
long text with special characters.

### Improvement 3: OPENAI_API_KEY for BrowserGym evaluators

**File:** `src/runner/browsergym_bridge.py`

Some WebArena tasks use LLM-based evaluation (OpenAI API). Added:
```python
os.environ.setdefault("OPENAI_API_KEY", "sk-litellm")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:4000")
```
Points evaluator requests at the LiteLLM proxy, avoiding the need for a real
OpenAI API key.

## Regression Results Comparison

| Version | Cases | Success | Bridge Crashes | 500ms Timeouts | Notes |
|---------|-------|---------|----------------|----------------|-------|
| v1 (pre-fix) | 12 | 1 (8%) | 2 (reddit 100,101) | ~15 | Wrong task IDs, wrong pages |
| v2 (task ID fix) | 12 | 1 (8%) | 3 (wikipedia) | ~8 | Correct routing, still 500ms |
| v3 (timeout fix) | 9 | 0 (0%) | 0 | 1 | Clean runs, agent answer issues |
| v4 (prompt fix) | 9 | TBD | 0 | TBD | Running... |

v3 had 0% success but all 9 cases ran cleanly — failures are agent answer quality
(long text, wrong format) not platform bugs. v4 should improve with concise answers.

## Known Limitations

1. **Wikipedia excluded** — all 16 tasks require map service. Re-enable after
   deploying map Docker container.
2. **BrowserGym timeout patch is fragile** — `sed` on installed package, lost on
   reinstall. Consider forking BrowserGym or contributing upstream fix.
3. **`send_msg_to_user` truncation** — 500 char limit may lose information for
   tasks requiring detailed answers. Monitor for false negatives.
