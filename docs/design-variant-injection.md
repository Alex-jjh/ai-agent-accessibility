# Design: Variant Injection into BrowserGym Bridge

## Problem

`runTrackA` (src/index.ts) applies variant DOM patches on a Playwright page, then
calls `executeAgentTask` which spawns an **independent** Python BrowserGym bridge
process. The bridge calls `env.reset()`, which navigates its own browser to the
target URL — loading the **original, unpatched** page. The agent never sees the
variant.

Result: scan metrics reflect the variant; agent behavior reflects base. The
independent variable (a11y variant level) is disconnected from the dependent
variable (agent success). All experiment data collected under this architecture
has this confound.

## Chosen Approach: 2a — Shared JS Patch Files

Extract the pure-JS DOM manipulation logic from each variant level into standalone
`.js` files. Both the TypeScript scanner path (Playwright `page.evaluate`) and the
Python bridge path (`env.unwrapped.page.evaluate`) read from the same source files.

### Why Not Alternatives

| Approach | Rejected Because |
|----------|-----------------|
| 1. Connect BrowserGym to Playwright's CDP | BrowserGym manages its own browser lifecycle; `env.reset()` would still reload the page and lose patches. Would require forking BrowserGym. |
| 3. Replace BrowserGym with custom executor | Rewrites action space parsing, observation extraction, episode management, reward computation. ~2 weeks of work + new bug surface. |

## Architecture

```
src/variants/patches/
├── inject/                    ← NEW: pure JS files (no TS, no imports)
│   ├── apply-low.js           ← extracted from applyLow's page.evaluate(...)
│   ├── apply-medium-low.js    ← extracted from applyMediumLow's page.evaluate(...)
│   └── apply-high.js          ← extracted from applyHigh's page.evaluate(...)
├── index.ts                   ← refactored: reads inject/*.js, calls page.evaluate(js)
└── revert.ts                  ← unchanged (revert only used in scanner path)
```

### JS File Contract

Each `inject/apply-*.js` file is a self-contained IIFE that:
- Takes no arguments (operates on `document` directly)
- Returns `Array<{ selector, changeType, original, modified }>` (the DomChange[] shape)
- Uses no Node.js APIs, no imports, no TypeScript — pure browser JS
- Is idempotent (safe to run twice on the same page)

Example structure:
```javascript
// inject/apply-low.js
(() => {
  const changes = [];
  // ... DOM manipulation logic extracted verbatim from applyLow ...
  return changes;
})();
```

### TypeScript Side (patches/index.ts)

```typescript
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function loadInjectScript(level: 'low' | 'medium-low' | 'high'): string {
  const filename = `apply-${level}.js`;
  return readFileSync(join(__dirname, 'inject', filename), 'utf-8');
}

async function applyLow(page: Page): Promise<DomChange[]> {
  const script = loadInjectScript('low');
  return page.evaluate(script);
}
// Same pattern for applyMediumLow, applyHigh
```

### Python Side (browsergym_bridge.py)

```python
import pathlib

INJECT_DIR = pathlib.Path(__file__).parent / ".." / "variants" / "patches" / "inject"

VARIANT_SCRIPTS = {
    "low": "apply-low.js",
    "medium-low": "apply-medium-low.js",
    "high": "apply-high.js",
}

def apply_variant(page, variant_level: str) -> list:
    """Apply variant DOM patches on the BrowserGym page."""
    if variant_level == "base":
        return []  # No-op
    script_file = VARIANT_SCRIPTS.get(variant_level)
    if not script_file:
        print(f"[bridge] Unknown variant level: {variant_level}", file=sys.stderr)
        return []
    js_code = (INJECT_DIR / script_file).read_text(encoding="utf-8")
    changes = page.evaluate(js_code)
    return changes or []
```

## Data Flow Changes

### Before (broken)

```
runTrackA:
  Playwright page → navigate → applyVariant → scan (sees variant)
  ↓
  executeAgentTask → spawn bridge.py → env.reset() → agent runs (sees BASE)
```

### After (fixed)

```
runTrackA:
  Playwright page → navigate → applyVariant → scan (sees variant)
  ↓
  executeAgentTask → spawn bridge.py → env.reset() → applyVariant → agent runs (sees variant)
```

Both paths apply the same variant from the same JS source. Scan and agent see
consistent DOM state.

## Interface Changes

### 1. BridgeTaskConfig (executor.ts)

```typescript
export interface BridgeTaskConfig {
  taskId: string;
  targetUrl: string;
  taskGoal: string;
  variantLevel: string;  // NEW: 'low' | 'medium-low' | 'base' | 'high'
}
```

### 2. executeAgentTask call site (index.ts)

```typescript
const trace = await executeAgentTask({
  taskId: params.taskId,
  agentConfig: params.agentConfig,
  taskGoal: params.taskId,
  targetUrl: appUrl,
  variant: variantLevel,  // already passed, just needs to flow to bridge
  attempt: params.attempt,
});
```

### 3. defaultBridgeSpawner (executor.ts)

Pass `variantLevel` through to the bridge config JSON:

```typescript
function defaultBridgeSpawner(scriptPath: string, taskConfig: BridgeTaskConfig): BridgeProcess {
  // taskConfig now includes variantLevel
  const child = spawn('python', [scriptPath, JSON.stringify(taskConfig)], { ... });
  ...
}
```

### 4. bridge.py main()

After `env.reset()` and timeout patching, before sending initial observation:

```python
obs, info = env.reset()
# ... existing timeout patches ...

# NEW: Apply variant DOM patches
variant_level = config.get("variantLevel", "base")
if variant_level != "base":
    try:
        page = env.unwrapped.page
        changes = apply_variant(page, variant_level)
        print(f"[bridge] Applied variant '{variant_level}': {len(changes)} DOM changes", file=sys.stderr)
        # Wait for DOM to settle after patches
        page.wait_for_timeout(500)
        # Re-capture observation after variant is applied
        # BrowserGym's obs is stale — we need the a11y tree from the patched DOM
        obs_after = env.unwrapped._get_obs()  # BrowserGym internal, may need fallback
        obs = {**obs, **obs_after} if obs_after else obs
    except Exception as e:
        print(f"[bridge] WARNING: variant injection failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# Send initial observation
obs_msg = extract_observation(obs, step=0)
```

## Observation Re-capture After Variant Injection

Critical detail: after applying variant patches, the BrowserGym observation
(especially `axtree_object`) is stale — it reflects the pre-patch DOM. The agent
needs to see the patched a11y tree.

Options (in order of preference):
1. Call `env.unwrapped._get_obs()` — BrowserGym internal method that re-captures
   the current page state. Works but depends on BrowserGym internals.
2. Call `page.locator('body').ariaSnapshot()` directly and replace `axtree_txt`
   in the observation dict. More robust but loses BrowserGym's bid annotations.
3. Execute a no-op action `noop()` via `env.step("noop()")` to trigger a fresh
   observation cycle. Cleanest API-wise but wastes one step.

Recommendation: Try option 1, fall back to option 3 if `_get_obs` is unavailable.

## File Extraction Checklist

For each variant level, extract the function body inside `page.evaluate(() => { ... })`
into the corresponding `inject/apply-*.js` file:

| Variant | Source in patches/index.ts | Target JS file | Lines (approx) |
|---------|--------------------------|----------------|-----------------|
| low | `applyLow` L37-175 | `inject/apply-low.js` | ~140 |
| medium-low | `applyMediumLow` L177-302 | `inject/apply-medium-low.js` | ~125 |
| high | `applyHigh` L304-527 | `inject/apply-high.js` | ~220 |

Each extraction is mechanical: wrap the function body in an IIFE, ensure `changes`
array is returned.

## Testing Strategy

### Unit Tests
- Existing `patches.test.ts` should continue to pass (TypeScript path unchanged
  in behavior, only refactored to read from JS files).
- New test: verify each `inject/*.js` file is valid JS that returns an array
  (parse + eval in a jsdom or Playwright context).

### Integration Test
- New test in `executor.test.ts`: mock bridge spawner that verifies
  `BridgeTaskConfig.variantLevel` is passed through correctly.
- Verify bridge.py receives and applies variant (can test with a mock page).

### E2E Validation
- Run a single test case with `low` variant on a local WebArena instance.
- Verify the agent's observation (axtree_txt) shows degraded accessibility
  (no landmarks, no ARIA attributes) — confirming the variant was applied
  in the BrowserGym environment.
- Compare scan results (from Playwright path) with agent observations (from
  bridge path) to confirm both see the same variant.

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| `env.unwrapped.page` API changes in future BrowserGym versions | Pin BrowserGym version; add try/except with clear error message |
| Variant patches interact differently with BrowserGym's action space | BrowserGym uses bid-based selectors from a11y tree, not CSS selectors. Variant patches that remove ARIA/roles will change the a11y tree, which is the intended experimental effect. |
| `_get_obs()` is a private API | Fall back to `env.step("noop()")` if unavailable |
| JS files get out of sync with TypeScript types | DomChange type is only used on the TS side for revert; the JS files return plain objects. Add a CI check that JS files parse without error. |
| Shadow DOM in `applyLow` makes elements invisible to BrowserGym's a11y tree | This is the intended effect for the `low` variant — agent should struggle with inaccessible elements. |

## Scope of Changes

| File | Change Type | Effort |
|------|------------|--------|
| `src/variants/patches/inject/apply-low.js` | NEW | Extract from index.ts |
| `src/variants/patches/inject/apply-medium-low.js` | NEW | Extract from index.ts |
| `src/variants/patches/inject/apply-high.js` | NEW | Extract from index.ts |
| `src/variants/patches/index.ts` | MODIFY | Refactor to read from inject/*.js |
| `src/runner/agents/executor.ts` | MODIFY | Add variantLevel to BridgeTaskConfig, pass through |
| `src/runner/browsergym_bridge.py` | MODIFY | Add apply_variant() after env.reset() |
| `src/index.ts` | MINOR | Ensure variant flows to executeAgentTask config |
| Tests | MODIFY | Update mocks for new BridgeTaskConfig shape |

Estimated effort: 1-2 days for implementation + testing.

## Other Confirmed Bugs to Fix in Same PR

While touching these files, also fix:

1. **Bug 3** (scheduler.ts): Move `completedCases.add(caseId)` before
   `persistRunState` — currently record is persisted but state isn't updated
   atomically, causing potential duplicate execution on crash recovery.

2. **Bug 4** (tier2/scan.ts `computeKeyboardNavigability`): Change
   `focusedTagNames` Set key to include a unique index or use a counter instead
   of a Set, so elements with identical tag/id/class aren't deduplicated.

3. **Bug 5** (patches/revert.ts): Add a `closed-shadow` case to
   `buildRevertScript` that unwraps the shadow DOM wrapper, or document that
   `revertVariant` is not supported for `low` variant.

4. **Bug 9** (patches/index.ts `applyLow`): Change `el.className.split(' ')`
   to `String(el.className).split(' ')` for SVG safety (consistency with
   `applyMediumLow` and `applyHigh`).
