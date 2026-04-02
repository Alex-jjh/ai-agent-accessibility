# Bug Fix Report — 2026-04-02 Round 3

Full codebase audit identified 5 confirmed bugs. 4 fixed in code, 1 documented as
known limitation. Commit `9589cf5`.

318 TS tests + 56 Python tests passing. `tsc --noEmit` clean.
Smoke test verified on EC2 with live WebArena — all 3 checks passed.

## Bug 6 [CRITICAL]: Agent runs on unpatched base page regardless of variant

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

## Bug 3 [LOW]: Scheduler persistence order — crash recovery may re-execute cases

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

## Bug 4 [MEDIUM]: Keyboard navigability metric systematically underestimates

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

## Bug 5 [MEDIUM]: revertVariant cannot undo low variant's closed Shadow DOM

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

## Bug 9 [TRIVIAL]: applyLow SVG className crash

**File:** `src/variants/patches/inject/apply-low.js`

**Root cause:** In the original `patches/index.ts`, `applyLow`'s step 1 (semantic
element replacement) used `el.className.split(' ')` without `String()` wrapping.
SVG elements have `className` as `SVGAnimatedString`, not `string` — calling
`.split()` on it throws TypeError. `applyMediumLow` and `applyHigh` already used
`String(el.className)` correctly.

**Impact:** Theoretical crash if a semantic element (`<nav>`, `<main>`, etc.) is an
SVG element. Practically near-zero probability since these tags are HTML-only.

**Fix:** All `inject/*.js` files consistently use `String(el.className)` everywhere.

## Smoke Test Verification

**Script:** `scripts/smoke-variant-injection.ts`

Runs ecommerce task 3 with `base` and `low` variants (maxSteps=5 each). Verifies:

1. **env.unwrapped.page accessible** — bridge stderr shows `Applied variant 'low': N DOM changes` with N > 0
2. **Observation re-capture** — low variant a11y tree lacks landmarks that base has
3. **Causal link** — observations differ between variants

**Usage:**
```bash
npx tsx scripts/smoke-variant-injection.ts
npx tsx scripts/smoke-variant-injection.ts --config ./config-regression.yaml
```

**Results saved to:** `data/smoke-variant/results.json`

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

Key evidence: Base a11y tree has `[235] banner ''` (from `<header>`), Low has no
banner — confirming `applyLow` replaced `<header>` with `<div>` in the BrowserGym
environment.

## Pilot 1 Data Implications

Pilot 1 (54 cases, 2026-04-01) was collected before Bug 6 was fixed. All variant
labels in the data are correct, but agent behavior was always base-equivalent.
The 4 successes (7.4% raw) reflect base-variant difficulty, not variant-specific
effects. This data should be treated as a baseline measurement, not as evidence
for or against the accessibility gradient hypothesis.

Pilot 2 (post-fix) will be the first valid test of the variant → agent success
causal relationship.

---

# Round 4 — Code Review Audit (2 fixes)

Full codebase audit. 2 P2 bugs fixed. 22 tests passing.

## Bug 10 [P2]: Vision mode history carries base64 screenshots → token explosion

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

## Bug 11 [P2]: detectHAL regex doesn't match BrowserGym action format → hallucination detection disabled

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

## Files Changed

| File | Change |
|------|--------|
| `src/runner/agents/executor.ts` | Strip base64 screenshots from vision history entries |
| `src/classifier/taxonomy/classify.ts` | Fix detectHAL regex to match BrowserGym action format |
