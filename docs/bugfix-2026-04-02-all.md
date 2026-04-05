# Bug Fix Report — 2026-04-02 (Consolidated)

All bug fixes and code review findings from 2026-04-02, consolidated from 5 rounds
of work. 318 TS tests + 56 Python tests passing after all fixes.

---

# Round 1 — Initial Review (7 bugs)

### Bug 1: config.yaml — cms/ecommerce port swap
- **File:** `config.yaml`
- **Issue:** `cms` was mapped to `:7770` (ecommerce storefront) and `ecommerce` to `:7780` (admin/CMS). Reversed.
- **Impact:** Full experiment would route agents to wrong apps. Pilot unaffected (uses config-pilot.yaml).
- **Fix:** Swapped URLs — cms→`:7780`, ecommerce→`:7770`.

### Bug 3: Keyboard navigability cycle detection fails without element id
- **File:** `src/scanner/tier2/scan.ts`
- **Issue:** Cycle detection condition `startInfo.id !== ''` meant Tab loop never terminated when starting element had no `id` (most pages). Would run to MAX_TAB_PRESSES (200) or 30s timeout.
- **Impact:** Inflated keyboardNavigability scores, extremely slow scans.
- **Fix:** Replaced id-dependent check with fingerprint comparison (`tag#id`). Also normalized `startInfo.tag` to lowercase for consistent matching.

### Bug 10: storeRecord called with caseId instead of runId
- **File:** `src/index.ts`
- **Issue:** `store.storeRecord(caseId, record, ...)` passed `caseId` as first arg, but `storeRecord` expects `runId`. Data stored under wrong directory path.
- **Impact:** Experiment data scattered across per-case directories instead of grouped under run directory.
- **Fix:** Changed to `store.storeRecord(run.runId, record, ...)` — but see Round 2 Bug R2-1 for the TDZ issue this introduced.

### Bug 2: CDP session leak in validateVariant
- **File:** `src/variants/validation/index.ts`
- **Issue:** `newCDPSession()` called without corresponding `detach()`. No try/finally.
- **Impact:** Resource leak — CDP sessions accumulate during experiment loops.
- **Fix:** Wrapped in try/finally with `await cdpSession.detach()`.

### Bug 9: hitStepLimit misses BrowserGym truncation
- **File:** `src/runner/agents/executor.ts`
- **Issue:** `hitStepLimit` only checked `steps.length >= maxSteps`. When BrowserGym set `obs.truncated=true` causing early exit, `steps.length < maxSteps` → classified as `failure` instead of `timeout`.
- **Impact:** Incorrect outcome classification for BrowserGym-truncated episodes.
- **Fix:** Added `envTruncated` flag, set when `obs.truncated` detected. `hitStepLimit = agentHitLimit || envTruncated`.

### Bug 5: Semantic HTML ratio denominator overlaps with numerator
- **File:** `src/scanner/tier2/scan.ts`
- **Issue:** `structuralTags` included semantic elements that were also in `SEMANTIC_ELEMENTS`.
- **Impact:** Ratio semantics unclear.
- **Fix:** Changed denominator to `div` + `span` only (non-semantic containers).

### Bug 13: Random Forest metrics evaluated on training set
- **File:** `analysis/models/secondary.py`
- **Issue:** Metrics computed on training data, severely overestimating performance.
- **Fix:** Replaced with `cross_val_predict`-based metrics when CV is possible.

---

# Round 2 — Full Audit (9 bugs + 1 feature)

### R2-1 [P0]: run.runId TDZ crash in runTrackA
- **File:** `src/index.ts`, `src/runner/scheduler.ts`
- **Issue:** `const run = await executeExperiment(...)` — the `runTestCase` callback references `run.runId` but runs inside `executeExperiment` before `run` is assigned. JavaScript TDZ causes `ReferenceError`.
- **Impact:** `ExperimentStore.storeRecord()` crashed on every test case. Scheduler's own `persistRecord` saved data, but structured store (scan-result.json, trace, classification split files) never worked.
- **Fix:** Added `onRunCreated` callback to `ExecuteExperimentOptions`. Scheduler calls it after creating the run object. `runTrackA` uses `let currentRunId` populated by the callback.

### R2-2 [P1]: HAR replay fidelity detection completely broken
- **File:** `src/recorder/replay/replay.ts`
- **Issue:** `routeFromHAR` with `notFound: 'abort'` causes Playwright to abort unmatched requests directly, never falling through to the custom `page.route('**/*')` handler. So `functionalUnmatched` is always empty, `coverageGap` always 0, `isLowFidelity` always false.
- **Impact:** Track B low-fidelity recording filter completely non-functional.
- **Fix:** Changed to always use `notFound: 'fallback'` so unmatched requests reach the custom handler for tracking and 404 response.

### R2-3 [P2]: revertVariant replace selector doesn't match post-mutation DOM
- **File:** `src/variants/patches/index.ts`, `src/variants/patches/revert.ts`
- **Issue:** `applyLow` replaces `<nav>` with `<div>`, but records selector as `nav#id`. Revert uses that selector — but the element is now a `<div>`, so `querySelector('nav#id')` finds nothing.
- **Impact:** `revertVariant` silently fails for all `replace` type changes.
- **Fix:** Stamp `data-variant-revert` attribute on replacement elements during apply. Revert uses `[data-variant-revert="..."]` selector.

### R2-4 [P2]: captureHar launches its own browser instead of using caller's
- **File:** `src/recorder/capture/capture.ts`, `src/recorder/types.ts`
- **Issue:** `captureHar` calls `chromium.launch()` internally, ignoring the `browser` instance passed by `runTrackB`.
- **Impact:** Two browser instances running simultaneously, resource waste.
- **Fix:** Added optional `browser` field to `HarCaptureOptions`. `captureHar` uses it when provided, only launches its own if not.

### R2-5 [P2]: post_hoc_power assumes 2 groups instead of actual variant count
- **File:** `analysis/models/primary.py`
- **Issue:** `n_per_group = n // 2` hardcodes 2 groups, but experiment has 4 variant levels.
- **Impact:** Overestimates per-group sample size → overestimates statistical power.
- **Fix:** Changed to `n // num_groups` where `num_groups` is derived from actual `a11y_variant_level` unique values.

### R2-6 [P2]: config loader merge() shallow-replaces nested objects
- **File:** `src/config/loader.ts`
- **Issue:** `merge()` does flat key-value override. If YAML provides partial `scoreRanges`, the entire default `scoreRanges` object is replaced, losing unspecified variant ranges.
- **Impact:** Partial config overrides silently lose defaults for nested objects.
- **Fix:** Changed `merge()` to recursive deep merge for nested plain objects.

### R2-7 [P3]: detectENF only finds first consecutive failure sequence
- **File:** `src/classifier/taxonomy/classify.ts`
- **Issue:** Breaks on first success after ≥3 consecutive failures, missing potentially longer sequences later in the trace.
- **Impact:** May underestimate F_ENF confidence.
- **Fix:** Changed to track the longest consecutive failure sequence across the entire trace.

### R2-8 [P3]: buildTasksPerApp comment has wrong task ID ranges
- **File:** `src/index.ts`
- **Issue:** Comment says "0-99: shopping_admin" but actual ranges are 0-2 (ecommerce_admin) and 3-99 (ecommerce storefront). Code was correct, only comment was wrong.
- **Fix:** Updated comment to match actual WebArena task ID ranges.

### R2-9: Unused imports and variables cleaned up
- **File:** `src/index.ts`
- **Issue:** `validateConfig`, `scanUrlsConcurrently`, `revertVariant`, `validateVariant`, `generateTestCases`, `parseTestCaseId`, `resetWebArenaApp`, `filterByReportingMode`, `scanner` variable — all imported/declared but never used.
- **Fix:** Removed all unused imports and the `buildScanner()` function + `scanner` variable.

### R2-10 [Feature]: LLM message history for multi-turn agent context
- **File:** `src/runner/agents/executor.ts`, `src/runner/types.ts`
- **Issue:** Each LLM call only sent system prompt + current observation. No conversation history. Agent couldn't remember previous actions, leading to repeated failures on multi-step tasks.
- **Impact:** Likely a major contributor to Pilot 1's 7.4% success rate.
- **Fix:** Added `maxHistorySteps` field to `AgentConfig` (default 6 via `?? 6` fallback). Executor now accumulates user/assistant message pairs and includes the last N turns (N = maxHistorySteps) in each LLM request. Configurable per agent config in YAML.

---

# Round 3 — Full Codebase Audit (5 bugs)

Commit `9589cf5`. Smoke test verified on EC2 with live WebArena — all 3 checks passed.

### Bug 6 [CRITICAL]: Agent runs on unpatched base page regardless of variant

**Root cause:** `runTrackA` (src/index.ts) applies variant DOM patches on a Playwright
page, then calls `executeAgentTask` which spawns an independent Python BrowserGym
bridge process. The bridge calls `env.reset()`, navigating its own browser to the
target URL — loading the original, unpatched page. The agent never sees the variant.

**Impact:** Scan metrics reflect the variant; agent behavior reflects base. The
independent variable (a11y variant level) is disconnected from the dependent variable
(agent success). All Pilot 1 data has this confound — variant labels in the data are
correct but agent behavior was always base-equivalent.

**Fix (method 2a — shared JS patch files):**

1. Extracted variant DOM manipulation logic from `patches/index.ts` into three
   standalone JS files under `src/variants/patches/inject/`:
   - `apply-low.js` (285 DOM changes on ecommerce)
   - `apply-medium-low.js`
   - `apply-high.js`

   Each file is a self-contained IIFE returning `DomChange[]`. No imports, no TS,
   pure browser JS. Both TypeScript and Python read from the same source.

2. Refactored `src/variants/patches/index.ts` to use `loadInjectScript()` +
   `page.evaluate(script)` instead of inline `page.evaluate(() => { ... })`.

3. Added `variantLevel: string` to `BridgeTaskConfig` in `executor.ts`.
   `executeAgentTask` now passes the variant through to the bridge config JSON.

4. Updated `src/runner/browsergym_bridge.py`:
   - Added `apply_variant(page, variant_level)` function that reads inject/*.js
   - After `env.reset()` and timeout patching, calls `apply_variant` on
     `env.unwrapped.page`
   - Re-captures observation via `env.unwrapped._get_obs()` (fallback: `env.step("noop()")`)
     so the agent's initial a11y tree reflects the patched DOM

**Data flow after fix:**
```
runTrackA:
  Playwright page → navigate → applyVariant → scan (sees variant)
  ↓
  executeAgentTask → spawn bridge.py → env.reset() → applyVariant → agent (sees variant)
```

Both paths read the same JS files. Scanner and agent see consistent DOM state.

**Files changed:**
| File | Change |
|------|--------|
| `src/variants/patches/inject/apply-low.js` | NEW — extracted from applyLow |
| `src/variants/patches/inject/apply-medium-low.js` | NEW — extracted from applyMediumLow |
| `src/variants/patches/inject/apply-high.js` | NEW — extracted from applyHigh |
| `src/variants/patches/index.ts` | Refactored to read inject/*.js |
| `src/runner/agents/executor.ts` | Added variantLevel to BridgeTaskConfig |
| `src/runner/browsergym_bridge.py` | Added apply_variant() after env.reset() |

**Design doc:** `docs/design-variant-injection.md`

### Bug 3 [LOW]: Scheduler persistence order — crash recovery may re-execute cases

**File:** `src/runner/scheduler.ts`, line 228

**Root cause:** Code order was `persistRecord` → `completedCases.add` → `persistRunState`.
If the process crashes between `persistRecord` and `persistRunState`, the run-state on
disk doesn't include the case in `completedCases`. On resume, the case is re-executed.

**Impact:** Duplicate execution wastes one agent run. No data corruption because
`persistRecord` writes to a deterministic file path (idempotent overwrite).

**Fix:** Moved `completedCases.add(caseId)` to immediately after `persistRecord`,
before `persistRunState`. Added comment explaining the ordering rationale.

Note: a tiny window remains between `add` and `persistRunState`. Fully atomic
persistence would require temp-file-then-rename, which is overkill for a research
platform where the cost of one duplicate run is negligible.

### Bug 4 [MEDIUM]: Keyboard navigability metric systematically underestimates

**File:** `src/scanner/tier2/scan.ts`, `computeKeyboardNavigability`

**Root cause:** Used a `Set<string>` with key `${el.tagName}#${el.id}.${el.className}`
to count unique focused elements. Multiple elements with identical tag/id/class
(e.g. several bare `<input>` elements) map to the same key → deduplicated → numerator
shrinks. Denominator (`totalFocusable`) counts all elements without dedup.

**Impact:** On form-heavy pages with many unlabeled inputs, keyboard navigability
ratio is systematically lower than reality. Affects Tier 2 metric accuracy.

**Fix:** Replaced Set-based dedup with a `data-kb-nav-idx` attribute stamped on each
element during the Tab traversal. Each element gets a unique index on first focus.
`focusedCount` is now a simple counter that increments when a new fingerprint is seen.
Trap detection still works via consecutive-same-fingerprint check.

**Test update:** `src/scanner/tier2/scan.test.ts` mock data updated to return
`fingerprint` field instead of `key` field.

### Bug 5 [MEDIUM]: revertVariant cannot undo low variant's closed Shadow DOM

**File:** `src/variants/patches/revert.ts`

**Root cause:** `applyLow` wraps interactive elements in closed Shadow DOM
(`wrapper.attachShadow({ mode: 'closed' })`). `revertVariant`'s `buildRevertScript`
uses `document.querySelector(selector)` to find elements, but closed shadow roots
are invisible to external queries. The original element cannot be found → revert
silently fails → DOM hash mismatch → `success: false`.

**Impact:** `revertVariant` always fails for `low` variant. Does not affect the
experiment pipeline because each test case creates a fresh browser context — revert
is only used for validation/debugging.

**Fix:** Documented as a known limitation in `revertVariant`'s JSDoc. The closed
Shadow DOM is architecturally irreversible from outside without maintaining a
reference to the shadow root (which is lost by design in `mode: 'closed'`).

### Bug 9 [TRIVIAL]: applyLow SVG className crash

**File:** `src/variants/patches/inject/apply-low.js`

**Root cause:** In the original `patches/index.ts`, `applyLow`'s step 1 (semantic
element replacement) used `el.className.split(' ')` without `String()` wrapping.
SVG elements have `className` as `SVGAnimatedString`, not `string` — calling
`.split()` on it throws TypeError. `applyMediumLow` and `applyHigh` already used
`String(el.className)` correctly.

**Impact:** Theoretical crash if a semantic element (`<nav>`, `<main>`, etc.) is an
SVG element. Practically near-zero probability since these tags are HTML-only.

**Fix:** All `inject/*.js` files consistently use `String(el.className)` everywhere.

### Smoke Test Verification

**Script:** `scripts/smoke-variant-injection.ts`

Runs ecommerce task 3 with `base` and `low` variants (maxSteps=5 each). Verifies:

1. **env.unwrapped.page accessible** — bridge stderr shows `Applied variant 'low': N DOM changes` with N > 0
2. **Observation re-capture** — low variant a11y tree lacks landmarks that base has
3. **Causal link** — observations differ between variants

**EC2 verification results (2026-04-02):**
```
[Check 1] env.unwrapped.page accessible:
  ✅ low variant case completed
  Bridge stderr: "[bridge] Applied variant 'low': 285 DOM changes"

[Check 2] Observation re-capture reflects patched DOM:
  Base: landmarks=true, aria=false
  Low:  landmarks=false, aria=false
  ✅ Low variant observation differs from base

[Check 3] Causal link — observations differ between variants:
  Base obs length: 9473 chars
  Low obs length:  6897 chars
  ✅ Observations are different

OVERALL: ✅ ALL CHECKS PASSED
```

### Pilot 1 Data Implications

Pilot 1 (54 cases, 2026-04-01) was collected before Bug 6 was fixed. All variant
labels in the data are correct, but agent behavior was always base-equivalent.
The 4 successes (7.4% raw) reflect base-variant difficulty, not variant-specific
effects. This data should be treated as a baseline measurement, not as evidence
for or against the accessibility gradient hypothesis.

---

# Round 4 — Code Review Audit (2 fixes)

### Bug 10 [P2]: Vision mode history carries base64 screenshots → token explosion

**File:** `src/runner/agents/executor.ts`

**Root cause:** `messageHistory.push({ role: 'user', content: userContent })` pushes
the raw `userContent` into history. In vision mode, `buildUserMessage` returns an
`object[]` containing `{ type: 'image_url', image_url: { url: 'data:image/png;base64,...' } }`.
Every historical step in the sliding window carries a full base64 screenshot (~100KB+).
With `maxHistorySteps=6`, that's 6 screenshots × ~100KB = ~600KB of base64 in every
LLM request, rapidly consuming the context window.

**Impact:** Vision mode token usage far exceeds expectations. Likely triggers context
overflow (F_COF) on longer episodes, or causes LLM API errors from oversized requests.

**Fix:** When pushing to `messageHistory`, vision mode content is stripped to text-only:
filter out `image_url` entries, keep only `text` entries joined as a string. The current
step still sends the full screenshot — only history entries lose the image data.

### Bug 11 [P2]: detectHAL regex doesn't match BrowserGym action format → hallucination detection disabled

**File:** `src/classifier/taxonomy/classify.ts`, `detectHAL`

**Root cause:** The hallucination detector extracted the action target using
`step.action.match(/element='([^']+)'/)`. BrowserGym actions use the format
`click("bid")`, `fill("bid", "text")`, `hover("bid")`, etc. The regex never matches,
so `actionTarget` is always empty, and the detector never fires.

**Impact:** F_HAL (hallucination) classification is effectively disabled. Agents acting
on non-existent elements are misclassified as F_ENF or F_REA instead.

**Fix:** Changed regex to `/(?:click|fill|hover|focus|press|type)\s*\(\s*"(\d+)"/`
which matches BrowserGym's actual action syntax and extracts the numeric bid. The bid
is then checked against the observation's a11y tree text.

---

# Round 5 — Regression Analysis (4 platform bugs + 3 agent improvements)

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

## Known Limitations

1. **Wikipedia excluded** — all 16 tasks require map service. Re-enable after
   deploying map Docker container.
2. **BrowserGym timeout patch is fragile** — `sed` on installed package, lost on
   reinstall. Consider forking BrowserGym or contributing upstream fix.
3. **`send_msg_to_user` truncation** — 500 char limit may lose information for
   tasks requiring detailed answers. Monitor for false negatives.

---

# Human Review Summary — Final Bug Triage

经人工 review 后的最终版本。去掉了不成立、重复、已修复的条目，调整了优先级。

## 需要修复 — 阻塞 regression

### BUG-01 [P0]: `determineOutcome` 成功判定逻辑脆弱
**文件**: `src/runner/agents/executor.ts` (L223-240)
**问题**: 成功判定依赖 `lastStep.action.includes('done')`。如果 LLM 输出
`send_msg_to_user("I cannot complete this, done trying")`，同时包含
"cannot complete" 和 "done"，由于 `includes('done')` 先于 `includes('cannot complete')`
匹配，会被错误判定为成功。更根本的问题是：BrowserGym 的 `obs.reward` 才是
ground truth 成功信号，但当前代码完全没用它。
**建议**: 优先用 `obs.reward > 0` 判定成功，`includes('done')` 作为 fallback。
同时调整 if 顺序，先检查 "cannot complete" 再检查 "done"。
**工作量**: ~30min

### BUG-04+05 [P0]: timeout/partial_success 丢失 + timeout 被误分类为 F_REA
**文件**: `src/runner/agents/executor.ts`, `src/index.ts`, `src/classifier/taxonomy/classify.ts`
**问题**:
1. `TaskOutcome.outcome` 被硬编码为 `trace.success ? 'success' : 'failure'`，
   丢掉了 `determineOutcome` 返回的 `'timeout'` 和 `'partial_success'` 状态。
2. Timeout 的 trace 进入 classifier 后没有专门的 timeout detector，
   默认 fallback 到 `F_REA`（reasoning error），这是不准确的。
**建议**:
- `TaskOutcome.outcome` 直接使用 `determineOutcome()` 的返回值，不要二值化。
- 在 `classifyFailure` 之前先判断 outcome type，timeout 直接标记为
  新增的 `F_TMO` 或在 ActionTrace 上标记 `failureType = 'timeout'`，不走 detector 链。
**工作量**: ~1h

### BUG-09 [P1]: `cleanAction` bracket stripping 不处理单引号 bid
**文件**: `src/runner/agents/executor.ts` (L156-174)
**问题**: Regex `\("?\[(\d+)\]"?` 只匹配双引号包裹的 `[bid]`。
LLM 偶尔输出单引号形式 `click('[413]')`，不会被 strip。
**建议**: Regex 改为 `\(["']?\[(\d+)\]["']?`，或在 cleanAction 开头统一把单引号替成双引号。
**工作量**: ~15min

### BUG-10 [P1]: `parseLlmResponse` fallback regex 缺少 `select_option`
**文件**: `src/runner/agents/executor.ts` (L177-220)
**问题**: Fallback regex 的 action 列表没有 `select_option`。
BrowserGym 支持 `select_option("bid", "value")` 用于下拉选择，
如果 LLM 输出这个动作且不在 JSON 格式中，会被 fallback 为 `noop()`。
**建议**: 在 regex alternation 中加上 `select_option`。
**工作量**: ~15min

## 需要修复 — 不阻塞 regression，后续处理

### BUG-07 [P1]: Track B `runTrackB` 导航到 `about:blank` 导致扫描空白页
**文件**: `src/index.ts` (runTrackB, ~L380)
**问题**: HAR replay session 创建后导航到 `about:blank`，不触发 HAR 匹配。
需要从 HAR 文件中提取原始 URL 来导航。Round 2 修了 `notFound: 'fallback'`
（R2-2），但导航目标的问题还在。
**状态**: Track B 还没跑过，不阻塞当前 regression。Pilot 2 前需修。

### BUG-17 [P2]: `loadConfig` 不验证 `tasksPerApp` 中的任务 ID 范围
**文件**: `src/config/loader.ts`
**问题**: 用户可以配置 `ecommerce: ["200", "201"]`（实际是 gitlab 的任务 ID），
不会收到任何警告。静默的任务路由错误。
**建议**: 在 validation 中加 task ID range 校验，至少 warn。

### BUG-19 [P2]: `scrubPii` 缺少 IP 地址和默认凭据脱敏
**文件**: `src/export/csv.ts`
**问题**: 没有处理内部 IP 地址（`10.0.1.49`）和 WebArena 默认凭据
（`admin/admin123`、`magentouser/MyPassword`）。
**建议**: 论文发布前补全。

## 已确认但不修 — Known Limitations / 设计决策

| Bug | 严重度 | 说明 |
|-----|--------|------|
| BUG-02 | P2 | detectENF 与 detectHAL confidence 相同时排序依赖 V8 实现细节 |
| BUG-03 | P2 | detectWEA 几乎永远不触发（BrowserGym 不提供 wrong element detail） |
| BUG-06 | P2 | Variant validation 权重与 pipeline 权重不一致（validation 当前未调用） |
| BUG-08 | P2 | Cohen's Kappa 配对方式依赖数组顺序（Review 模块未启用） |
| BUG-21 | P2 | `_VARIANT_ORDER` 等距整数编码假设（论文中讨论） |
| BUG-25 | 设计决策 | `config-pilot.yaml` 省略 medium-low（有意减少 case 数量） |

## 不成立 / 已修复 / 重复 — 排除

| Bug | 判定 | 原因 |
|-----|------|------|
| BUG-11 | ❌ 自己撤回 | ARN 格式正确 |
| BUG-12 | P2 极低概率 | className 纯空格在 WebArena 页面不太可能出现 |
| BUG-13 | P2 低概率 | 起始元素通常是 body，Tab 回 body 概率低 |
| BUG-14 | ❌ 不成立 | BrowserGym 基于 Gymnasium，5值返回是标准 API |
| BUG-15 | ❌ 不成立 | spawn 有 stderr handler 在消费数据 |
| BUG-18 | ❌ 不成立 | caseId 包含 attempt 号，不会覆盖 |
| BUG-20 | ❌ 不是 bug | 返回完整 components 是 feature |
| BUG-22 | ❌ 无影响 | eps 重复定义，值相同 |
| BUG-23 | ❌ 不触发 | acquire/release 配对使用 |
| BUG-24 | ❌ 重复 | = Round 3 Bug 6，已修复 |

## 修复优先级总结

| # | Bug | 优先级 | 工作量 |
|---|-----|--------|--------|
| 1 | BUG-01: determineOutcome 用 BrowserGym reward 判定成功 | 🔴 P0 | 30min |
| 2 | BUG-04+05: timeout/partial_success 透传 + classifier 处理 | 🔴 P0 | 1h |
| 3 | BUG-09: bracket stripping 加单引号支持 | 🟡 P1 | 15min |
| 4 | BUG-10: parseLlmResponse 加 select_option | 🟡 P1 | 15min |
| 5 | BUG-07: Track B 导航逻辑（Pilot 2 前） | 🟡 P1 | 1h |
| 6 | BUG-17: task ID range 校验（建议） | 🔵 P2 | 30min |
| 7 | BUG-19: PII 脱敏补全（论文前） | 🔵 P2 | 30min |
