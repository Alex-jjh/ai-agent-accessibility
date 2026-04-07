# AI Agent Accessibility Platform — Project Steering

## Project Overview

Empirical research platform studying web accessibility vs AI agent task success.
Dual-track: Track A (WebArena controlled experiments), Track B (HAR replay ecological survey).
Six modules: Scanner, Variants, Runner, Classifier, Recorder, Analysis (Python).

## Current Status

Tasks 1–22 complete (all 6 modules implemented, 334 TS + 67 Python tests passing).
Scanner verified on real websites (EC2 + local). LiteLLM → Bedrock verified.
Infrastructure: private subnet + SSM (no public access, burner account compliant).
Pilot 1 completed 2026-04-01 — 54 cases, 4 successes (7.4% raw / 66.7% effective).
Root cause analysis identified 5 failure categories; 3 P0 code fixes applied and pushed.
Round 5 regression (2026-04-02): task ID mapping corrected from test.raw.json,
BrowserGym 500ms→3000ms timeout fixed, wikipedia excluded (map dependency),
agent prompt tuned for concise answers, send_msg_to_user sanitized.

Screening completed (2026-04-03):
- ecommerce_admin: 2/12 success (16.7%) — tasks 4, 14. Admin routing fixed (/admin path).
- ecommerce storefront: 3/10 success (30%) — tasks 23, 24, 26 (review search type).
- reddit: 4/9 success (44%) — tasks 27, 29, 30, 67 (forum navigation type).
- Regression v5: 3/9 (33%) — platform stable, zero crashes/timeouts/ValueError.

Shopping login fix completed (2026-04-04):
- Root cause: BrowserGym hooks ALL Playwright navigation after env.reset() +
  Magento regenerates PHPSESSID on login + Docker URL misconfiguration.
- Fix: HTTP login via Python requests (bypasses browser entirely), cookie injection
  via context.add_cookies(), reload via env.step(goto(start_url)).
- Verified: Task 47 agent sees "Sign Out", navigates to My Account, sees order history.
- Tasks 47-50 now viable for Pilot 2.

Literature-driven experiment hardening completed (2026-04-05):
- Low variant patches aligned to Ma11y [ISSTA 2024] WCAG failure operators.
  8 direct matches + 4 novel extensions (E1-E4) documented.
  3 new operators added: F42 (link→span), F77 (duplicate IDs), F55 (focus blur).
- Vision-only agent control condition implemented. ObservationMode extended to
  'text-only' | 'vision' | 'vision-only'. Vision-only agent receives screenshot
  only (no a11y tree) — serves as causal control since DOM mutations change
  semantics but not visual appearance.
- Semantic density metric defined: interactive_nodes / total_a11y_tree_tokens.
  Python module with CLI and 11 tests. Quantifies "token inflation pathway".
- Aegis failure taxonomy comparison: 6 modes vs our 12 types, 5 novel types.
- Pilot 3 config updated: 2 agents × 6 tasks × 4 variants × 5 reps = 240 runs.

Pilot 4 in progress (2026-04-07): 240 cases with Plan D variant injection.
- Plan D: context.route() + deferred patch (load+500ms) + MutationObserver guard
- Smoke test confirmed: ecom:23 low 0/1, no tablist/tabpanel in trace (goto escape blocked)
- 52/240 completed before bridge hang fix; resumed with 120s bridge timeout + vision skip
- Mid-run text-only: low 25% → ml/base/high 100% (step function replicates)
- Three-layer hang prevention: bridge 120s timeout, wall-clock 10min, vision-only skip

Open issues:
- Pilot 4 running (~188 cases remaining, ~10-12 hours)
- reddit × vision-only may still be slow (large SoM overlay on 200+ elements)
- Composite score compression persists (0.386–0.461 vs 0.00–1.00)

Pilot 3a completed (2026-04-05): 120 cases, 87/120 (72.5%).
- Monotonic gradient: low 20% → ml 86.7% → base 90% → high 93.3%
- Low vs base: χ²=29.70, p<0.0001, V=0.704. Core finding confirmed.
- Dose-response is step function: low→ml jump = 91% of total effect.
- Two failure pathways: token inflation (admin:4, reddit:67) + content invisibility (ecom:23/24/26).

Pilot 3b completed (2026-04-05/06): 240 cases (text-only + vision-only).
- Text-only replicates 3a: 71.7% overall, low vs base p<0.001.
- Vision-only failed first run (LiteLLM config not loaded), re-running.
- Variant injection race condition discovered: goto() reload clears patches non-deterministically.
  Fixed with three-layer defense (init_script + listeners + secondary verification).
- SoM overlay implemented for vision-only agent (PIL-based bid label rendering).

Next: Analyze Pilot 3b vision-only results when re-run completes.
See docs/platform-engineering-log.md for full bug catalog and analysis reports.

Pilot 4 completed (2026-04-07): 240/240 cases, N=240 full design matrix.
- Text-only: low 23.3% → ml 100% → base 86.7% → high 76.7%
- Vision-only (SoM): low 0% → ml 23.3% → base 20% → high 30%
- Primary stat: low vs base χ²=24.31, p<0.000001, Cramér's V=0.637
- Plan D verified: 33/33 goto traces show persistent degradation
- Three failure pathways: content invisibility, token inflation, phantom bids

CUA (Computer Use Agent) integration completed (2026-04-07):
- Pure coordinate-based vision agent via Anthropic Computer Use tool + Bedrock
- LiteLLM cannot forward computer_use → direct boto3 Bedrock Converse API
- Architecture: bridge self-driven (cua_bridge.py), fully decoupled from existing modes
- Smoke test: ecom:23 base, reward=1.0, 11 steps, 139K tokens, 72s
- Two rounds of code review: 11 issues found, all fixed
- Pilot 4 CUA running: 6 tasks × 4 variants × 5 reps = 120 cases

CUA known issue — low variant cross-layer visual effects:
- Patch 3 (label removal): form label TEXT disappears from visual rendering
- Patch 5 (Shadow DOM): elements may lose external CSS styles
- Patch 9 (table→div): table layout may break visually
- If CUA shows a11y gradient, need to distinguish: semantic-only vs visual confound
- Tasks ecom:23/24/26 (review reading) are less affected than admin:4 (form-heavy)

Next steps — Task expansion (incremental):
- Current: 6 tasks across 2 sites (ecommerce + reddit). Goal: 12+ tasks across 3 sites.
- Expansion strategy: smoke test per task → verify → add to matrix
- Priority 1: GitLab tasks (new site, Vue.js DOM, different structure)
- Priority 2: Form submission tasks (ARIA label + form association coverage)
- Priority 3: Dropdown/select tasks (combobox/listbox role)
- Each new task: base smoke → low variant smoke → add to full matrix
- GitLab variant patches may need site-specific tuning (Vue.js rendering)

## WebArena Task ID Mapping (CRITICAL)

Task IDs are interleaved across sites in webarena/test.raw.json — NOT contiguous ranges.
Each task_id maps to exactly one site. Using wrong IDs = silent misrouting.

```
shopping_admin (Magento backend :7780):  182 tasks, first: 0,1,2,3,4,5,6,11,12,13
shopping       (Magento storefront :7770): 192 tasks, first: 21,22,23,24,25,26,47,48
reddit         (Postmill :9999):         114 tasks, first: 27,28,29,30,31,66,67,68
gitlab         (:8023):                  196 tasks, first: 44,45,46,102,103,104,105
wikipedia      (Kiwix :8888):             16 tasks, first: 265,266,267,268,424,425
map            (:3000):                  128 tasks — NOT DEPLOYED, excluded
```

NEVER assume contiguous ranges (e.g. "reddit=100-199" is WRONG).
Always use explicit tasksPerApp in YAML config, or verify against test.raw.json.

## Deployment Rules (CRITICAL)

- ALWAYS run experiments via nohup or the launch-*.sh scripts on EC2.
  SSM sessions disconnect after ~20 min idle. Running `npx tsx` directly
  in foreground WILL be killed when the session drops. Use:
  `bash scripts/launch-pilot3b.sh` (nohup wrapper with PID tracking)
  or: `nohup npx tsx scripts/run-pilot3.ts --config X.yaml > log 2>&1 &`
- Burner accounts auto-close if EC2 has public access (0.0.0.0/0 inbound SG)
- ALWAYS use private subnet + SSM Session Manager (no SSH, no public IP)
- Use `terraform apply` from infra/ — it handles all security correctly
- NEVER manually create EC2 via AWS console
- Connect via: `aws ssm start-session --target <instance-id>`
- Platform EC2 (runs code): `i-0288f77960077b755`
- WebArena EC2 (runs Docker): `i-0c916d784df56d796`
- See docs/deployment.md for full guide including all known issues

## EC2 Reproducibility Rules (CRITICAL)

- NEVER make manual edits on EC2 that aren't tracked in the repo
- All config, scripts, and code changes MUST go through git (edit locally → push → pull on EC2)
- EC2 instances are ephemeral — may be redeployed on different machines at any time
- The only exception is one-time env setup (BrowserGym timeout sed patch, pip installs)
  which MUST be documented in scripts/ec2-setup.sh so they can be re-applied
- Data files (experiment results, screening data) are synced via S3, not stored only on EC2
- `task-site-mapping.json` (repo root) is committed — do NOT regenerate on EC2 unless
  the webarena package version changes
- ALWAYS download experiment data to local workspace and read actual trace files
  before drawing conclusions. Never assume outcomes from summary statistics alone —
  trace-level analysis has repeatedly revealed unexpected mechanisms (variant escape,
  false positives, stochastic divergence points) that summary numbers hide.

## Architecture Rules

- TypeScript (ES2022, strict mode) for modules 1–5; Python for module 6
- Modules communicate via TypeScript interfaces and JSON files, no runtime RPC
- Experiment matrix scheduler (Module 3) orchestrates sequential execution
- Python Analysis Engine consumes CSV exports only
- Always read before you edit if the file exists
- Commit when a feature is completed
- TRACE IS KING: After any change to variant injection, observation extraction,
  bridge communication, or agent prompts, ALWAYS run a smoke test (config-reinject-smoke.yaml),
  download the trace data, and read the actual agent observations step-by-step before
  concluding the fix works. Summary statistics (success rates) are not sufficient —
  multiple times a "fix" appeared to work from summary numbers but trace analysis
  revealed the underlying mechanism was unchanged (e.g., goto escape, Magento re-rendering).
  Never assume a code change affects what the agent sees without reading the trace.

## Coding Standards

- All metric values must be 0.0–1.0 inclusive (use `isValidMetricValue`)
- Use `.js` extensions in all TypeScript imports (ESM)
- Prefer `Promise.allSettled()` for parallel operations that should not fail together
- Log errors and continue — never crash the pipeline on a single URL/tool failure
- Every module exports from its `index.ts` barrel file
- Tests use vitest; run with `npx vitest --run`
- Type check with `npx tsc --noEmit`

## Key Design Decisions

- Composite Score is supplementary — primary analysis uses criterion-level feature vectors
- Vision-only agent is a control condition (expected weak/null a11y gradient).
  Uses screenshot only, no a11y tree. Causal logic: if text-only drops but
  vision-only stays constant across variants → a11y tree is the causal factor.
  NOTE: Pilot 4 proved SoM overlays depend on DOM (phantom bids at low=0%).
- CUA agent is the TRUE pure-vision control (zero DOM dependency).
  Uses Anthropic Computer Use tool via direct Bedrock Converse API (bypasses LiteLLM).
  Bridge self-driven: cua_bridge.py runs agent loop internally, executor just waits.
  ObservationMode: 'text-only' | 'vision' | 'vision-only' | 'cua'
  CUA bridge read timeout: wallClockTimeoutMs + 30s (default 630s, vs 120s for others).
  Screenshot eviction: sliding window keeps last 5 turns to avoid 20MB Bedrock limit.
- Variant levels: low (0.0–0.25), medium-low (0.25–0.50), base (0.40–0.70), high (0.75–1.0)
- Medium-Low variant models real-world pseudo-compliance (ARIA present, handlers missing)
- Low variant operators grounded in Ma11y [ISSTA 2024] WCAG failure techniques:
  8 direct matches (F2, F42, F44, F55, F65, F68, F77, F91, F96) + 4 novel extensions
- Semantic density metric: interactive_nodes / total_a11y_tree_tokens (novel contribution)
- A11y Tree stability: poll at 2s intervals, SHA-256 hash comparison, 30s timeout
- Config: only `webarena.apps` is required; all other fields have documented defaults
- Failure taxonomy: 12 types across 5 domains (accessibility, model, environmental, task, unclassified)
  — 5 types novel vs Aegis [2025] (F_KBT, F_PCT, F_SDI, F_AMB, F_UNK)

## Key Reference Files (repo root)

- `test.raw.json` — WebArena's 812 task definitions (from `webarena` Python package).
  Contains task_id, sites, start_url, intent, eval config, and ground truth for each task.
  Eval types: `string_match` (substring), `url_match`, `program_html` (DOM check),
  `llm_eval` (GPT-4 judge — requires OPENAI_API_KEY via LiteLLM proxy).
- `task-site-mapping.json` — Derived lookup: task_id → site name. Used by screen-tasks
  to filter tasks by app. Regenerate only if webarena package version changes.

## File Structure

```
src/scanner/     — Tier 1 (axe-core + Lighthouse) + Tier 2 (CDP metrics)
src/variants/    — DOM patch engine for 4 accessibility variant levels
src/runner/      — Agent executor, LLM backend, experiment matrix scheduler
  cua_bridge.py  — CUA agent loop (boto3 Bedrock, coordinate actions, screenshot eviction)
src/classifier/  — Auto-classifier (12 failure types) + manual review
src/recorder/    — HAR capture and replay for Track B
src/config/      — YAML/JSON config loader with validation and defaults
src/export/      — Manifest, CSV export, JSON store
analysis/        — Python: CLMM, GEE, Random Forest + SHAP, semantic density
docs/            — Engineering log, analysis reports, literature comparisons
scripts/         — Launch scripts, smoke tests, analysis tools
  smoke-cua-*.   — CUA API verification scripts (LiteLLM + Bedrock direct)
```

## Key Documentation Files

- `docs/platform-engineering-log.md` — Full bug/fix/regression history
- `docs/ma11y-operator-mapping.md` — Ma11y operator audit + novel extensions
- `docs/aegis-taxonomy-comparison.md` — Failure taxonomy comparison with Aegis
- `docs/pilot2-trace-deep-dive.md` — Pilot 2 trace analysis
- `docs/screening-analysis.md` — Task screening results

## Spec Reference

Full requirements, design, and tasks at:
#[[file:.kiro/specs/ai-agent-accessibility-platform/requirements.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/design.md]]
#[[file:.kiro/specs/ai-agent-accessibility-platform/tasks.md]]
